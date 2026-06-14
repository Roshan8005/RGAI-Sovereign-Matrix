#!/usr/bin/env python3
"""
RGAI Edge PACS (chunked ternary compression + manifest)

Saves original DICOM, splits PixelData into chunks, converts chunks to Sah ternary,
gzip-compresses each chunk, optionally encrypts, writes part files and a manifest JSON.
"""
import os
import sqlite3
import hashlib
import gzip
import json
import time
from pathlib import Path
from math import ceil

from pydicom.dataset import Dataset
from pydicom.filewriter import write_file_meta_info
from pynetdicom import AE, evt, StoragePresentationContexts, QueryRetrievePresentationContexts

# Optional imports from repo
try:
    from ternary_math_compressor import SahTernaryCompressor
except Exception:
    SahTernaryCompressor = None

try:
    from mesh_crypto import MeshCrypto
except Exception:
    MeshCrypto = None

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACS_STORAGE_DIR = os.path.join(BASE_DIR, "sovereign_vault", "pacs_data")
COMPRESSED_DIR = os.path.join(BASE_DIR, "sovereign_vault", "pacs_compressed")
DB_PATH = os.path.join(BASE_DIR, "local_ledger.db")
os.makedirs(PACS_STORAGE_DIR, exist_ok=True)
os.makedirs(COMPRESSED_DIR, exist_ok=True)

# Chunk size configurable via env (bytes). Default 64 KiB safe for low-memory.
CHUNK_SIZE = int(os.environ.get("RGAI_CHUNK_SIZE", str(64 * 1024)))

# --- DB setup / migration (idempotent create) ---
def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacs_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            PatientID TEXT,
            PatientName TEXT,
            StudyInstanceUID TEXT,
            Modality TEXT,
            FilePath TEXT,
            CompressedManifestPath TEXT,
            PartsCount INTEGER,
            OriginalPixelSHA256 TEXT,
            SizeBytes INTEGER,
            CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Helpers
def sha256_bytes(b: bytes):
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def save_original_dicom(dataset, file_meta, dest_path):
    with open(dest_path, 'wb') as f:
        f.write(b'\x00' * 128)
        f.write(b'DICM')
        write_file_meta_info(f, file_meta)
        dataset.save_as(f, write_like_original=False)

def optionally_encrypt_bytes(data: bytes, credentials_path: str = None):
    if MeshCrypto is None or credentials_path is None:
        return data, False
    try:
        crypto = MeshCrypto.load_or_generate(credentials_path)
        enc = crypto.encrypt(data)
        return enc, True
    except Exception as e:
        print(f"[Edge PACS] Encryption skipped: {e}")
        return data, False

def compress_chunk(chunk_bytes: bytes, compressor: SahTernaryCompressor):
    """
    Convert chunk bytes -> ternary matrix -> serialize -> gzip -> return bytes
    """
    matrix = compressor.string_to_ternary_stream(chunk_bytes)
    serialized = compressor.serialize_matrix_to_string(matrix)  # text of trits
    gz = gzip.compress(serialized.encode('utf-8'), compresslevel=6)
    return gz

# Main C-STORE handler
def handle_store(event):
    try:
        ds = event.dataset
        ds.file_meta = event.file_meta

        patient_id = str(ds.get("PatientID", "UNKNOWN_ID"))
        patient_name = str(ds.get("PatientName", "UNKNOWN_NAME"))
        study_uid = str(ds.get("StudyInstanceUID", "UNKNOWN_STUDY"))
        modality = str(ds.get("Modality", "UNKNOWN"))
        sop_instance = getattr(ds, "SOPInstanceUID", f"{int(time.time())}")
        safe_stem = f"{patient_id}_{sop_instance}"

        # Save original viewer-friendly DICOM
        orig_fname = f"{safe_stem}.dcm"
        orig_path = os.path.join(PACS_STORAGE_DIR, orig_fname)
        save_original_dicom(ds, event.file_meta, orig_path)
        print(f"[Edge PACS] Saved original DICOM {orig_fname}")

        # Prepare chunking manifest
        compressed_manifest = {
            "sop_instance_uid": sop_instance,
            "patient_id": patient_id,
            "study_instance_uid": study_uid,
            "modality": modality,
            "chunk_size": CHUNK_SIZE,
            "parts": [],
            "created_at": int(time.time()),
            "encryption": False
        }

        # PixelData presence check
        original_pixel_sha = None
        parts_written = 0

        if hasattr(ds, "PixelData") and ds.PixelData:
            pixel_bytes = ds.PixelData
            original_pixel_sha = sha256_bytes(pixel_bytes)
            total_len = len(pixel_bytes)
            total_parts = ceil(total_len / CHUNK_SIZE)

            if SahTernaryCompressor is None:
                raise RuntimeError("SahTernaryCompressor not available for chunk compression.")

            compressor = SahTernaryCompressor()
            credentials_file = os.path.join(BASE_DIR, "phone_credentials.key")  # optional
            for idx in range(total_parts):
                start = idx * CHUNK_SIZE
                end = min(start + CHUNK_SIZE, total_len)
                chunk = pixel_bytes[start:end]
                try:
                    gz_bytes = compress_chunk(chunk, compressor)  # serialized trits gzipped
                except Exception as e:
                    print(f"[Edge PACS] Chunk compress failed idx={idx}: {e}")
                    raise

                # optional encrypt
                enc_bytes, enc_flag = optionally_encrypt_bytes(gz_bytes, credentials_file)
                compressed_manifest["encryption"] = compressed_manifest["encryption"] or enc_flag

                part_name = f"{safe_stem}.part{idx:04d}.rgai.gz"
                part_path = os.path.join(COMPRESSED_DIR, part_name)
                with open(part_path, "wb") as pf:
                    pf.write(enc_bytes)

                part_sha = sha256_bytes(enc_bytes)
                compressed_manifest["parts"].append({
                    "index": idx,
                    "filename": part_name,
                    "size": len(enc_bytes),
                    "sha256": part_sha,
                    "original_range": [start, end]
                })
                parts_written += 1
                print(f"[Edge PACS] Wrote part {part_name} ({len(enc_bytes)} bytes)")

            compressed_manifest["parts_count"] = parts_written
            compressed_manifest["original_pixel_sha256"] = original_pixel_sha
        else:
            print("[Edge PACS] No PixelData present; skipping compression/manifest parts.")
            compressed_manifest["parts_count"] = 0
            compressed_manifest["original_pixel_sha256"] = None

        # Save manifest file
        manifest_name = f"{safe_stem}.manifest.json"
        manifest_path = os.path.join(COMPRESSED_DIR, manifest_name)
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(compressed_manifest, mf, indent=2)

        # Insert metadata record in DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pacs_metadata
            (PatientID, PatientName, StudyInstanceUID, Modality, FilePath, CompressedManifestPath, PartsCount, OriginalPixelSHA256, SizeBytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, patient_name, study_uid, modality, orig_path, manifest_path, parts_written, original_pixel_sha, os.path.getsize(orig_path)))
        conn.commit()
        conn.close()

        print(f"[Edge PACS] Manifest saved: {manifest_name} | parts: {parts_written}")
        # Optional webhook to orchestrator (uncomment and configure)
        # requests.post("http://127.0.0.1:5000/api/v1/jobs/pacs", json={"source":"PACS","manifest":manifest_path})

        return 0x0000

    except Exception as e:
        print(f"[Edge PACS] ERROR in store handler: {e}")
        return 0xC210

# Basic C-FIND handler (unchanged)
def handle_find(event):
    identifier = event.identifier
    qpid = identifier.get("PatientID", "")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if qpid:
        cursor.execute("SELECT PatientID, PatientName, StudyInstanceUID, Modality FROM pacs_metadata WHERE PatientID = ?", (qpid,))
    else:
        cursor.execute("SELECT PatientID, PatientName, StudyInstanceUID, Modality FROM pacs_metadata LIMIT 10")
    recs = cursor.fetchall()
    conn.close()

    for r in recs:
        ds = Dataset()
        ds.PatientID = r[0]; ds.PatientName = r[1]; ds.StudyInstanceUID = r[2]; ds.Modality = r[3]
        ds.QueryRetrieveLevel = identifier.get("QueryRetrieveLevel", "PATIENT")
        yield (0xFF00, ds)

# Bootstrap AE
def main():
    setup_database()
    ae = AE(ae_title=b'RGAI_PACS')
    ae.supported_contexts = StoragePresentationContexts + QueryRetrievePresentationContexts
    handlers = [(evt.EVT_C_STORE, handle_store), (evt.EVT_C_FIND, handle_find)]
    print("[RGAI PACS] Sovereign Edge PACS listening on port 11112...")
    ae.start_server(('0.0.0.0', 11112), evt_handlers=handlers)

if __name__ == "__main__":
    main()
