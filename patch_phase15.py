import os
import re

# Patch rgai_phone_node.py
with open("rgai_phone_node.py", "r", encoding="utf-8") as f:
    node_code = f.read()

# Replace get_or_create_node_credentials
node_code = re.sub(
    r"def get_or_create_node_credentials\(\):[\s\S]*?return private_key, public_key_hash",
    """def get_or_create_node_credentials():
    from mesh_crypto import MeshCrypto
    crypto = MeshCrypto.load_or_generate(CREDENTIALS_FILE)
    return crypto.get_private_bytes().hex(), crypto.get_public_bytes().hex()""",
    node_code
)

# In run_mobile_worker_node
node_code = node_code.replace(
    "private_key, public_key = get_or_create_node_credentials()",
    "private_key, public_key = get_or_create_node_credentials()\n    from mesh_crypto import MeshCrypto\n    node_crypto = MeshCrypto.load_or_generate(CREDENTIALS_FILE)"
)

# Patching UDP dispatch in rgai_phone_node.py
# Find where it does the HTTP registration and gets server_public_key
node_code = node_code.replace(
    "peers = res_data.get(\"peers\", {})",
    """peers = res_data.get("peers", {})
                    server_pub_hex = res_data.get("server_public_key")
                    if server_pub_hex and not getattr(node_crypto, "shared_secret", None):
                        node_crypto.derive_shared_secret(bytes.fromhex(server_pub_hex))
                        print("[Crypto] Derived Shared Secret with Master Router via HKDF!")"""
)

encryption_logic = """        if getattr(node_crypto, 'shared_secret', None):
            # Encrypt the payload and prepend magic byte + node_id
            encrypted_payload = node_crypto.encrypt(encoded_message)
            header = b"\\xCF" + NODE_ID.encode('utf-8').ljust(32, b'\\0')
            transmit_message = header + encrypted_payload
        else:
            transmit_message = encoded_message
            
        try:
            sock.sendto(transmit_message, ('255.255.255.255', PORT))"""

# Using simple string replacement instead of regex to avoid escape issues
target_str = "try:\n            sock.sendto(encoded_message, ('255.255.255.255', PORT))"
node_code = node_code.replace(target_str, encryption_logic)

# Patch peers sendto
node_code = node_code.replace(
    "sock.sendto(encoded_message, (peer_ip, peer_port))",
    "sock.sendto(transmit_message, (peer_ip, peer_port))"
)

with open("rgai_phone_node.py", "w", encoding="utf-8") as f:
    f.write(node_code)


# Patch ternary_mesh_router.py
with open("ternary_mesh_router.py", "r", encoding="utf-8") as f:
    router_code = f.read()

# Inside listen_for_peers
router_decrypt_logic = """
                # Decrypt TEMPEST Scrambler traffic
                if len(data) > 33 and data[0] == 0xCF:
                    try:
                        sender_node_id = data[1:33].rstrip(b'\\0').decode('utf-8')
                        ciphertext = data[33:]
                        
                        import json, os
                        from mesh_crypto import MeshCrypto
                        
                        router_crypto = MeshCrypto.load_or_generate(os.path.join(BASE_DIR, "router_credentials.key"))
                        
                        # Load peer's public key from discovery registry
                        active_nodes_path = os.path.join(BASE_DIR, "active_nodes.json")
                        if os.path.exists(active_nodes_path):
                            with open(active_nodes_path, 'r') as f:
                                registry = json.load(f)
                                if sender_node_id in registry:
                                    peer_pub_hex = registry[sender_node_id].get("public_key")
                                    if peer_pub_hex:
                                        router_crypto.derive_shared_secret(bytes.fromhex(peer_pub_hex))
                                        data = router_crypto.decrypt(ciphertext)
                                        #print(f"[Crypto] Decrypted {len(data)} bytes from {sender_node_id}")
                    except Exception as e:
                        print(f"[Crypto Error] Failed to decrypt packet: {e}")
                        continue
"""
router_code = router_code.replace(
    "packets_list = []",
    "packets_list = []\n" + router_decrypt_logic
)

with open("ternary_mesh_router.py", "w", encoding="utf-8") as f:
    f.write(router_code)

print("Patch applied to both files successfully.")
