"""
Mesh Cryptography Module.

Handles all secure peer-to-peer communications for the Sovereign Matrix.
Implements X25519 Elliptic Curve Diffie-Hellman Key Exchange and the
ChaCha20Poly1305 stream cipher for zero-trust UDP encryption on the edge.
"""
import os
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

class MeshCrypto:
    """
    RGAI Sovereign Matrix - TEMPEST Scrambler
    Handles X25519 Elliptic Curve Diffie-Hellman Key Exchange and ChaCha20Poly1305 Stream Cipher.
    """
    
    def __init__(self, private_bytes=None):
        if private_bytes:
            self.private_key = x25519.X25519PrivateKey.from_private_bytes(private_bytes)
        else:
            self.private_key = x25519.X25519PrivateKey.generate()
            
        self.public_key = self.private_key.public_key()
        self.shared_secret = None
        self.chacha = None
        
    @classmethod
    def load_or_generate(cls, filename="router_credentials.key"):
        """
        Loads the private key from the given filename if it exists,
        otherwise generates a new keypair and saves it to disk.
        """
        import os
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                private_bytes = f.read()
            return cls(private_bytes=private_bytes)
        else:
            instance = cls()
            with open(filename, 'wb') as f:
                f.write(instance.get_private_bytes())
            return instance
            
    def get_public_bytes(self):
        """Returns the serialized raw public bytes for X25519."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
    def get_private_bytes(self):
        """Returns the serialized raw private bytes for X25519."""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
    def derive_shared_secret(self, peer_public_bytes):
        """
        Derives the Diffie-Hellman shared secret using HKDF.
        """
        peer_public_key = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared = self.private_key.exchange(peer_public_key)
        
        self.shared_secret = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'rgai_mesh_v1'
        ).derive(shared)
        
        self.chacha = ChaCha20Poly1305(self.shared_secret)
        return self.shared_secret
        
    def encrypt(self, plaintext_bytes):
        """
        Encrypts the plaintext using ChaCha20Poly1305 with a random 12-byte nonce.
        Prepends the nonce to the resulting ciphertext.
        """
        if not self.chacha:
            raise ValueError("Shared secret not derived. Cannot encrypt.")
            
        nonce = os.urandom(12)
        ciphertext = self.chacha.encrypt(nonce, plaintext_bytes, None)
        return nonce + ciphertext
        
    def decrypt(self, payload_bytes):
        """
        Decrypts a payload encrypted by ChaCha20Poly1305.
        Expects the first 12 bytes of the payload to be the nonce.
        """
        if not self.chacha:
            raise ValueError("Shared secret not derived. Cannot decrypt.")
            
        if len(payload_bytes) < 12:
            raise ValueError("Payload too short to contain nonce.")
            
        nonce = payload_bytes[:12]
        ciphertext = payload_bytes[12:]
        return self.chacha.decrypt(nonce, ciphertext, None)
