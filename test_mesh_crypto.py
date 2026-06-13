from mesh_crypto import MeshCrypto

def test_tempest_scrambler():
    print("==========================================================")
    print(" [TEST] RGAI TEMPEST SCRAMBLER UNIT TEST")
    print("==========================================================")
    
    # 1. Initialize Nodes (Keypair Generation)
    print("[1] Generating X25519 Identity for Edge Node...")
    edge_node = MeshCrypto()
    print(f"    Edge Public Key: {edge_node.get_public_bytes().hex()[:16]}...")

    print("[2] Generating X25519 Identity for Master Router...")
    master_router = MeshCrypto()
    print(f"    Router Public Key: {master_router.get_public_bytes().hex()[:16]}...")

    # 2. Key Exchange (Diffie-Hellman)
    print("[3] Performing Diffie-Hellman Handshake...")
    edge_secret = edge_node.derive_shared_secret(master_router.get_public_bytes())
    router_secret = master_router.derive_shared_secret(edge_node.get_public_bytes())
    
    if edge_secret == router_secret:
        print(f"    [OK] Shared Secret Match! ({edge_secret.hex()[:16]}...)")
    else:
        print("    [ERROR] Shared Secret Mismatch!")
        return

    # 3. Payload Encryption (ChaCha20)
    print("[4] Encrypting raw ternary payload at Edge Node...")
    raw_payload = b'{"task_id": "0xE1_VISION", "matrix": [-1, 0, 1, 1, 0, -1]}'
    ciphertext = edge_node.encrypt(raw_payload)
    print(f"    Ciphertext length: {len(ciphertext)} bytes")
    print(f"    Encrypted noise: {ciphertext.hex()[:32]}...")

    # 4. Payload Decryption (ChaCha20)
    print("[5] Decrypting payload at Master Router...")
    decrypted_payload = master_router.decrypt(ciphertext)
    
    if decrypted_payload == raw_payload:
        print(f"    [OK] Decryption Success: {decrypted_payload.decode('utf-8')}")
    else:
        print("    [ERROR] Decryption Failed!")

    print("==========================================================")
    print(" TEMPEST Scrambler Crypto-Suite is Operational!")
    print("==========================================================")

if __name__ == "__main__":
    test_tempest_scrambler()
