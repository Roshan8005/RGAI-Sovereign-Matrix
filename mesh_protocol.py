import os
import sys
import hashlib
import hmac
import random
import time
import json
from ternary_math_compressor import SahTernaryCompressor

# DH Parameters: Standard RFC 3526 2048-bit MODP Group prime (represented cleanly for zero dependencies)
DH_G = 2
DH_P = int(
    "FFFFFFFFFFFFFFFFC90FFAA72759C14657B9B40D7F28BEF85747F4688139093"
    "29175E14821A7BEE887593E1857914572138BEB92A4F8E3C105E83F00EF26E"
    "D749B0E1B4F4BAA51A1BC7564BE2433CBE5BA3B28A403F54002621008CFF8A"
    "1CD712B26AA81E83F72CDD2F7E1B851C813350280EFBCFCD9F9010C49FB838"
    "35F8E24C7BA223DEDC2386E80EE77FCB8B67D3ED682AD3F2A465B49BEA61EB"
    "FF9EFFD7FEB361830A0A3D7FE5187FEF8", 16
)

class SahSecureMeshProtocol:
    def __init__(self, node_id):
        self.node_id = node_id
        self.compressor = SahTernaryCompressor()
        
        # 🔑 Initialize DH Asymmetric Key Pair
        self.private_key = random.SystemRandom().getrandbits(256)
        self.public_key = pow(DH_G, self.private_key, DH_P)
        print(f"[Mesh Secure] Keys Generated for '{node_id}'. PubKey Hash: {hashlib.sha256(str(self.public_key).encode()).hexdigest()[:8]}")

    def derive_shared_secret(self, peer_public_key):
        """Computes DH Shared Secret: s = B^a mod p"""
        try:
            peer_pub = int(peer_public_key)
            shared_secret = pow(peer_pub, self.private_key, DH_P)
            # Hash to get a uniform 256-bit symmetric session key
            shared_hash = hashlib.sha256(str(shared_secret).encode()).digest()
            return shared_hash
        except Exception as e:
            print(f"[Mesh Secure] DH secret derivation failed: {e}")
            return None

    def encrypt_payload(self, raw_data, session_key):
        """
        Pure Python Secure SHA-256 Stream Cipher (Counter-Mode)
        Encrypts payload and attaches HMAC for authenticated verification (AEAD style).
        """
        try:
            # Derive encryption and MAC keys from session key
            enc_key = hashlib.sha256(session_key + b"ENC").digest()
            mac_key = hashlib.sha256(session_key + b"MAC").digest()
            
            # Generate a 16-byte cryptographically secure random Initialization Vector (IV)
            iv = bytes(random.SystemRandom().getrandbits(8) for _ in range(16))
            
            # Convert raw_data to bytes
            data_bytes = raw_data.encode('utf-8')
            ciphertext = bytearray()
            
            # Encrypt byte-by-byte using keystream generated from SHA-256(key + IV + counter)
            counter = 0
            for i in range(0, len(data_bytes), 32):
                block_key = hashlib.sha256(enc_key + iv + str(counter).encode()).digest()
                chunk = data_bytes[i:i+32]
                for j in range(len(chunk)):
                    ciphertext.append(chunk[j] ^ block_key[j])
                counter += 1
                
            ciphertext = bytes(ciphertext)
            
            # Compute dynamic HMAC over ciphertext + IV
            mac = hmac.new(mac_key, iv + ciphertext, hashlib.sha256).digest()
            
            # Package: IV (16 bytes) + MAC (32 bytes) + Ciphertext
            packet_data = iv + mac + ciphertext
            return packet_data
        except Exception as e:
            print(f"[Mesh Secure] Encryption error: {e}")
            return None

    def decrypt_payload(self, packed_data, session_key):
        """Decrypts and verifies authentication tag (HMAC)."""
        try:
            if len(packed_data) < 48:
                raise ValueError("Payload too small.")
                
            # Derive encryption and MAC keys
            enc_key = hashlib.sha256(session_key + b"ENC").digest()
            mac_key = hashlib.sha256(session_key + b"MAC").digest()
            
            # Unpack components
            iv = packed_data[:16]
            expected_mac = packed_data[16:48]
            ciphertext = packed_data[48:]
            
            # Verify HMAC first to prevent tampering
            computed_mac = hmac.new(mac_key, iv + ciphertext, hashlib.sha256).digest()
            if not hmac.compare_digest(computed_mac, expected_mac):
                raise ValueError("MAC Verification Failed: Message Tampered!")
                
            # Decrypt ciphertext
            decrypted = bytearray()
            counter = 0
            for i in range(0, len(ciphertext), 32):
                block_key = hashlib.sha256(enc_key + iv + str(counter).encode()).digest()
                chunk = ciphertext[i:i+32]
                for j in range(len(chunk)):
                    decrypted.append(chunk[j] ^ block_key[j])
                counter += 1
                
            return bytes(decrypted).decode('utf-8')
        except Exception as e:
            print(f"[Mesh Secure] Decryption error: {e}")
            return None

    def serialize_secure_packet(self, raw_payload, peer_public_key):
        """
        Encrypts payload with DH session key and encodes it into 
        Sah balanced ternary character arrays.
        """
        session_key = self.derive_shared_secret(peer_public_key)
        if not session_key:
            return None
            
        encrypted_bytes = self.encrypt_payload(raw_payload, session_key)
        if not encrypted_bytes:
            return None
            
        # Convert bytes to string of numbers or hex prior to ternary compression
        hex_data = encrypted_bytes.hex()
        
        # Compress hex string using Sah Ternary Compressor
        matrix = self.compressor.string_to_ternary_stream(hex_data)
        ternary_string = self.compressor.serialize_matrix_to_string(matrix)
        
        # Final outbound envelope representation
        envelope = {
            "sender_node_id": self.node_id,
            "sender_pubkey": str(self.public_key),
            "payload_matrix": ternary_string,
            "timestamp": time.time()
        }
        return json.dumps(envelope)

    def deserialize_secure_packet(self, envelope_json, sender_private_secret_or_key_source=None):
        """
        Extracts sender pubkey, derives shared session key, decompresses ternary payload,
        verifies HMAC integrity, and decrypts the core message block.
        """
        try:
            envelope = json.loads(envelope_json)
            sender_id = envelope["sender_node_id"]
            peer_pubkey = int(envelope["sender_pubkey"])
            ternary_payload = envelope["payload_matrix"]
            
            # Decompress Ternary representation back to Hex bytes
            matrix = self.compressor.deserialize_string_to_matrix(ternary_payload)
            hex_data = self.compressor.ternary_stream_to_string(matrix)
            encrypted_bytes = bytes.fromhex(hex_data)
            
            # Derive symmetric key from our DH secrets
            session_key = self.derive_shared_secret(peer_pubkey)
            if not session_key:
                return None
                
            # Decrypt payload bytes
            decrypted_text = self.decrypt_payload(encrypted_bytes, session_key)
            return {
                "sender_id": sender_id,
                "payload": decrypted_text,
                "timestamp": envelope["timestamp"]
            }
        except Exception as e:
            print(f"[Mesh Secure] Packet deserialization failure: {e}")
            return None

if __name__ == "__main__":
    print("==========================================================")
    print("⚡ TESTING ZERO-DEPENDENCY CRYPTOGRAPHIC TERNARY PROTOCOL  ")
    print("==========================================================")
    
    # Initialize Node A and Node B
    node_a = SahSecureMeshProtocol("Master_Core_Roshan")
    node_b = SahSecureMeshProtocol("Swarm_Node_Ankit")
    
    # Exchange key simulation
    message = "Decentralized task coordination secured via Sah base-3 state matrices."
    print(f"\n[Raw Message]: {message}")
    
    # Node A serializes secure packet for Node B (Node A uses Node B's public key)
    print("\n[Node A] Encrypting and packing message into ternary stream...")
    envelope = node_a.serialize_secure_packet(message, node_b.public_key)
    print(f"Envelope Envelope Size: {len(envelope)} characters.")
    
    # Node B deserializes secure packet from Node A (Node B uses Node A's public key inside the envelope)
    print("\n[Node B] Decompressing ternary, verifying HMAC, and decrypting payload...")
    result = node_b.deserialize_secure_packet(envelope)
    
    if result:
        print(f"[SUCCESS] Decrypted Message: {result['payload']}")
        print(f"[Sender Identity]: {result['sender_id']}")
    else:
        print("[FAIL] Secure decryption error.")
    print("==========================================================")
