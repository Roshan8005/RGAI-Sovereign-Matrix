#!/usr/bin/env python3
"""
RGAI Test Harness (Standalone CLI)
- Generates a dummy DICOM with PixelData
- Runs chunked ternary compression (using ternary_math_compressor.SahTernaryCompressor)
- Writes parts and a manifest to sovereign_vault/pacs_compressed
- Serves the compressed directory over HTTP
- Node-side downloads manifest and parts, decompresses & deserializes per-chunk,
  streams reassembly of pixel bytes, verifies SHA256, and writes reconstructed DICOM

Usage:
  python rgai_test_harness.py            # run with defaults
  python rgai_test_harness.py --pixel-bytes 131072 --chunk-size 65536
"""
import os
import sys
import argparse
import json
import gzip
import hashlib
import time
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request
from math import ceil
from pathlib import Path

# pydicom required
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.filewriter import write_file_meta_info
from pydicom.uid import generate_uid, ExplicitVRLittleEndian

# Try to import repo compressor
try:
    from ternary_math_compressor import SahTernaryCompressor
except Exception as e:
    print("Error importing ternary_math_compressor.SahTernaryCompressor:", e)
    print("Ensure ternary_math_compressor.py is in PYTHONPATH. Exiting.")
    sys.exit(2)

# Config default directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACS_STORAGE_DIR = os.path.join(BASE_DIR, "sovereign_vault", "pacs_data")
COMPRESSED_DIR = os.path.join(BASE_DIR, "sovereign_vault", "pacs_compressed")
os.makedirs(PACS_STORAGE_DIR, exist_ok=True)
os.makedirs(COMPRESSED_DIR, exist_ok=True)

def sha256_bytes(b: bytes):
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def create_dummy_dicom(patient_id: str, patient_name: str, rows: int, cols: int, pixel_bytes: bytes, out_path: str):
    ds = Dataset()
    ds.PatientID = patient_id
    ds.PatientName = patient_name
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = generate_uid()
    ds.Modality = "CT"
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelRepresentation = 0
    ds.PixelData = pixel_bytes

    # Minimal file meta
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = generate_uid()
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    # Save file
    with open(out_path, "wb") as f:
        f.write(b'\x00' * 128)
        f.write(b'DICM')
        write_file_meta_info(f, file_meta)
        ds.save_as(f, write_like_original=False)
    return ds, file_meta

def compress_and_chunk_pixeldata(sop_stem: str, pixel_bytes: bytes, chunk_size: int, compressor: SahTernaryCompressor):
    total_len = len(pixel_bytes)
    total_parts = ceil(total_len / chunk_size)
    manifest = {
        "sop_instance_uid": sop_stem,
        "chunk_size": chunk_size,
        "parts_count": total_parts,
        "original_pixel_sha256": sha256_bytes(pixel_bytes),
        "created_at": int(time.time()),
        "parts": []
    }

    for idx in range(total_parts):
        start = idx * chunk_size
        end = min(start + chunk_size, total_len)
        chunk = pixel_bytes[start:end]

        matrix = compressor.string_to_ternary_stream(chunk)
        serialized = compressor.serialize_matrix_to_string(matrix)
        gz = gzip.compress(serialized.encode("utf-8"), compresslevel=6)

        part_name = f"{sop_stem}.part{idx:04d}.rgai.gz"
        part_path = os.path.join(COMPRESSED_DIR, part_name)
        with open(part_path, "wb") as pf:
            pf.write(gz)
        part_sha = sha256_bytes(gz)
        manifest["parts"].append({
            "index": idx,
            "filename": part_name,
            "size": len(gz),
            "sha256": part_sha,
            "range": [start, end]
        })
        print(f"[PACS] Wrote part {part_name} size={len(gz)}")
    return manifest

def write_manifest(manifest: dict):
    manifest_name = f"{manifest['sop_instance_uid']}.manifest.json"
    manifest_path = os.path.join(COMPRESSED_DIR, manifest_name)
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)
    return manifest_name, manifest_path

def start_http_server(directory: str):
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"[HTTP] Serving {directory} at http://127.0.0.1:{port}/")
    return httpd, port

def fetch_bytes(uri: str, timeout=10):
    parsed = urlparse(uri)
    if parsed.scheme in ("http", "https"):
        req = urllib.request.Request(uri, headers={"User-Agent": "RGAI-TestHarness/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    else:
        with open(uri, "rb") as f:
            return f.read()

def node_assemble_from_manifest(manifest_url: str, out_dir: str, compressor: SahTernaryCompressor):
    os.makedirs(out_dir, exist_ok=True)
    manifest_bytes = fetch_bytes(manifest_url)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    sop = manifest.get("sop_instance_uid", f"rgai_{int(time.time())}")
    out_path = os.path.join(out_dir, f"{sop}.pixels.bin")
    if os.path.exists(out_path):
        os.remove(out_path)

    base_url = manifest_url.rsplit("/", 1)[0] + "/"
    for part in sorted(manifest.get("parts", []), key=lambda p: p["index"]):
        part_uri = base_url + part["filename"]
        print(f"[Node] Downloading part {part['index']} from {part_uri}")
        gz_bytes = fetch_bytes(part_uri)
        actual_sha = sha256_bytes(gz_bytes)
        if actual_sha != part["sha256"]:
            raise RuntimeError(f"SHA mismatch for part {part['filename']}: expected {part['sha256']} got {actual_sha}")
        serialized_trits = gzip.decompress(gz_bytes).decode("utf-8")
        matrix = compressor.deserialize_string_to_matrix(serialized_trits)
        chunk_bytes = compressor.ternary_stream_to_bytes(matrix)
        with open(out_path, "ab") as outf:
            outf.write(chunk_bytes)
        print(f"[Node] Appended part {part['index']} ({len(chunk_bytes)} bytes)")

    assembled_sha = sha256_bytes(open(out_path, "rb").read())
    if manifest.get("original_pixel_sha256") and assembled_sha != manifest["original_pixel_sha256"]:
        raise RuntimeError(f"Final pixel SHA mismatch: {assembled_sha} != {manifest['original_pixel_sha256']}")
    print(f"[Node] Assembly complete. Output: {out_path}, SHA256: {assembled_sha}")
    return out_path, assembled_sha

def reconstruct_dicom_from_original(orig_path: str, assembled_pixel_path: str, out_recon_path: str):
    from pydicom import dcmread
    ds = dcmread(orig_path)
    with open(assembled_pixel_path, "rb") as f:
        pixels = f.read()
    ds.PixelData = pixels
    ds.save_as(out_recon_path, write_like_original=False)
    print(f"[Recon] Reconstructed DICOM saved: {out_recon_path}")

def main():
    parser = argparse.ArgumentParser(description="RGAI Test Harness: chunking + manifest + node assemble")
    parser.add_argument("--pixel-bytes", type=int, default=64*1024, help="Total PixelData size in bytes for dummy DICOM (default 64KiB)")
    parser.add_argument("--rows", type=int, default=256, help="Rows for dummy DICOM (used for metadata, not strict)")
    parser.add_argument("--cols", type=int, default=256, help="Cols for dummy DICOM (metadata)")
    parser.add_argument("--chunk-size", type=int, default=64*1024, help="Chunk size in bytes (default 64KiB)")
    parser.add_argument("--serve", action="store_true", default=True, help="Start local HTTP server to serve compressed dir (default True)")
    args = parser.parse_args()

    pixel_bytes = bytes((i % 256) for i in range(args.pixel_bytes))
    patient_id = "TEST_PATIENT"
    patient_name = "RGAI^Test"
    rows = args.rows
    cols = args.cols

    safe_stem = f"{patient_id}_{int(time.time())}"
    orig_fname = f"{safe_stem}.dcm"
    orig_path = os.path.join(PACS_STORAGE_DIR, orig_fname)
    ds, file_meta = create_dummy_dicom(patient_id, patient_name, rows, cols, pixel_bytes, orig_path)
    print(f"[Harness] Dummy DICOM created: {orig_path} (Pixel bytes: {len(pixel_bytes)})")

    compressor = SahTernaryCompressor()
    manifest = compress_and_chunk_pixeldata(safe_stem, pixel_bytes, args.chunk_size, compressor)
    manifest_name, manifest_path = write_manifest(manifest)
    print(f"[Harness] Manifest written: {manifest_path}")

    if args.serve:
        httpd, port = start_http_server(COMPRESSED_DIR)
        manifest_url = f"http://127.0.0.1:{port}/{manifest_name}"
    else:
        manifest_url = manifest_path

    out_dir = os.path.join(BASE_DIR, "node_recon")
    assembled_path, assembled_sha = node_assemble_from_manifest(manifest_url, out_dir, compressor)

    recon_path = os.path.join(out_dir, f"{safe_stem}.recon.dcm")
    reconstruct_dicom_from_original(orig_path, assembled_path, recon_path)

    print("[Harness] Roundtrip verified successfully.")
    print("Locations:")
    print(" - Original DICOM:", orig_path)
    print(" - Manifest:", manifest_path)
    print(" - Compressed parts dir:", COMPRESSED_DIR)
    print(" - Assembled pixels:", assembled_path)
    print(" - Reconstructed DICOM:", recon_path)

    if args.serve:
        print("[Harness] HTTP server will keep running for 8 seconds (so you can fetch files manually if needed)...")
        time.sleep(8)
        httpd.shutdown()
        print("[HTTP] Server shutdown.")

if __name__ == "__main__":
    main()
