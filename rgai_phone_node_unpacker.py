import time
#!/usr/bin/env python3
"""
Manifest-based unpacker for .rgai.gz parts (Edge Node)

- Fetch manifest (local path or HTTP URL)
- For each part: download, optional decrypt, gunzip, deserialize trits -> bytes
- Stream-append bytes to output file (no large-memory buffering)
- Verify per-part SHA and final original pixel SHA

Usage:
  python rgai_phone_node_unpacker.py <manifest_path_or_url> [out_dir] [credentials_path]
"""
import os
import sys
import json
import gzip
import hashlib
import urllib.request
from urllib.parse import urlparse

try:
    from ternary_math_compressor import SahTernaryCompressor
except Exception:
    SahTernaryCompressor = None

try:
    from mesh_crypto import MeshCrypto
except Exception:
    MeshCrypto = None


def fetch_bytes(uri: str, timeout=10):
    parsed = urlparse(uri)
    if parsed.scheme in ("http", "https"):
        req = urllib.request.Request(uri, headers={"User-Agent": "RGAI-Node/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    else:
        # Treat as local file path
        with open(uri, "rb") as f:
            return f.read()


def decrypt_if_needed(data: bytes, credentials_path: str = None):
    if MeshCrypto is None or credentials_path is None:
        return data
    try:
        crypto = MeshCrypto.load_or_generate(credentials_path)
        return crypto.decrypt(data)
    except Exception as e:
        print(f"[Node Unpacker] Decrypt failed/skip: {e}")
        return data


def assemble_rgai_manifest(manifest_uri: str, out_dir: str, credentials_path: str = None):
    os.makedirs(out_dir, exist_ok=True)

    # Load manifest (local path or http)
    manifest_bytes = fetch_bytes(manifest_uri)
    manifest = json.loads(manifest_bytes.decode("utf-8"))

    compressor = SahTernaryCompressor() if SahTernaryCompressor else None
    if compressor is None:
        raise RuntimeError("SahTernaryCompressor not available on node.")

    safe_stem = manifest.get("sop_instance_uid", f"rgai_{int(time.time())}")
    out_path = os.path.join(out_dir, f"{safe_stem}.pixels.bin")
    # Remove if exists
    if os.path.exists(out_path):
        os.remove(out_path)

    parts = manifest.get("parts", [])
    for part in sorted(parts, key=lambda x: x["index"]):
        part_filename = part["filename"]
        # Determine part URI: if manifest_uri is local file, parts likely local; if manifest_uri was HTTP, parts may be relative to same base
        parsed_manifest = urlparse(manifest_uri)
        if parsed_manifest.scheme in ("http", "https"):
            base = manifest_uri.rsplit("/", 1)[0]
            part_uri = base + "/" + part_filename
        else:
            # local directory
            part_dir = os.path.dirname(manifest_uri)
            part_uri = os.path.join(part_dir, part_filename)

        print(f"[Node Unpacker] Fetching part {part['index']} from {part_uri}")
        enc_bytes = fetch_bytes(part_uri)
        # optional decrypt
        payload = decrypt_if_needed(enc_bytes, credentials_path)
        # gunzip decompress
        try:
            serialized_trits = gzip.decompress(payload).decode("utf-8")
            
        except Exception as e:
            raise RuntimeError(f"GZIP decompression failed: {e}")

        # deserialize and convert to raw bytes
        matrix = compressor.deserialize_string_to_matrix(serialized_trits)
        chunk_bytes = compressor.ternary_stream_to_bytes(matrix)

        # Write/append to output file (streaming)
        with open(out_path, "ab") as outf:
            outf.write(chunk_bytes)

        # Verify part SHA optionally
        actual_sha = hashlib.sha256(enc_bytes).hexdigest()
        if part.get("sha256") and part["sha256"] != actual_sha:
            raise RuntimeError(f"SHA mismatch for part {part_filename}: expected {part['sha256']} != {actual_sha}")

        print(f"[Node Unpacker] Appended part {part['index']} ({len(chunk_bytes)} bytes)")

    # Final verification against manifest original_pixel_sha256 if present
    if manifest.get("original_pixel_sha256"):
        with open(out_path, "rb") as rf:
            full_sha = hashlib.sha256(rf.read()).hexdigest()
        if full_sha != manifest["original_pixel_sha256"]:
            raise RuntimeError(f"Final pixel SHA mismatch: {full_sha} != {manifest['original_pixel_sha256']}")
        else:
            print("[Node Unpacker] Final pixel SHA verified OK.")

    print(f"[Node Unpacker] Assembly complete: {out_path}")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rgai_phone_node_unpacker.py <manifest_path_or_url> [out_dir] [credentials_path]")
        sys.exit(1)
    manifest = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/rgai_recon"
    cred = sys.argv[3] if len(sys.argv) > 3 else None
    assemble_rgai_manifest(manifest, out, cred)

