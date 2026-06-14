# PR: Edge PACS — chunked ternary compression + manifest + node unpacker (with test harness)

## Summary
This PR introduces a lightweight, edge-native PACS pipeline for the RGAI Sovereign Matrix designed for offline-first, privacy-preserving clinical edge inference.

Files added (branch: `rgai/edge-pacs-chunking`):
- `rgai_edge_pacs.py` — C-STORE handler that saves original DICOMs, chunks PixelData into configurable-size blocks, converts each block to the Sah balanced-ternary serialized stream, gzip-compresses, optionally encrypts (when `phone_credentials.key` exists), writes per-part files and a manifest JSON, and inserts metadata into `local_ledger.db`.
- `rgai_phone_node_unpacker.py` — Node-side manifest consumer and streaming assembler: downloads each part (local or HTTP), optional decryption, gzip decompress, ternary deserialize, stream-append into reconstructed pixel-bytes, verifies per-part SHA256 and final pixel SHA.
- `rgai_test_harness.py` — Standalone CLI test harness to simulate full roundtrip locally: generates a dummy DICOM, runs PACS chunking, serves parts over a local HTTP server, runs the node assembler, verifies SHA and reconstructs a DICOM file.
- `migrate_pacs_db.py` — Idempotent DB migration helper that ensures `pacs_metadata` contains `CompressedManifestPath`, `PartsCount`, and `OriginalPixelSHA256` columns.

## How to review / test locally (quick)
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure `ternary_math_compressor.py` is in the repo root (it is present) and importable.
3. Run DB migration (idempotent):
   ```bash
   python migrate_pacs_db.py
   ```
4. Run the test harness (local roundtrip):
   ```bash
   python rgai_test_harness.py
   ```
   Expected: dummy DICOM created in `sovereign_vault/pacs_data`, compressed parts + manifest in `sovereign_vault/pacs_compressed`, temporary HTTP server serves parts, node assembles parts under `node_recon/`, final reconstructed DICOM created, and SHA verification passes.

5. Optional: Run PACS AE (to exercise C-STORE handler):
   ```bash
   python rgai_edge_pacs.py
   # use any DICOM SCU tool to C-STORE to AE title RGAI_PACS at port 11112
   ```

6. Node-side assembly (manual):
   ```bash
   python rgai_phone_node_unpacker.py http://<MASTER_IP>:<PORT>/<manifest.json> ./node_recon [phone_credentials.key]
   ```

## Configuration & notes
- Default chunk size is 64 KiB. Override with env var `RGAI_CHUNK_SIZE` (bytes).
- Encryption is optional. If `phone_credentials.key` exists, parts will be encrypted using `mesh_crypto` (if implemented). Default behavior is unencrypted to simplify local dev and tests.
- The compressor currently serializes trits as characters ('T','0','1') and uses gzip. Future binary packing of trits will yield much better size efficiency.

## Migration
- If `local_ledger.db` exists, run `python migrate_pacs_db.py` to add missing columns. The script is idempotent and safe to run multiple times.

## Next steps / Roadmap (recommended)
1. Trit → binary packing: pack balanced-trits into compact bytes to remove textual overhead prior to gzip — large wins for compression and memory.
2. Streaming authenticated encryption: ChaCha20-Poly1305 per-chunk with nonce and AAD to secure parts during transit without buffering the whole chunk.
3. Serve manifests and part files behind authenticated endpoints (Discovery server) with TLS and access control.
4. Full DICOM de-identification workflow and compliance documentation before any production clinical data usage.

## PR checklist (for reviewers)
- [ ] Manifest schema matches expectations and includes per-part SHA
- [ ] DB migration ran successfully and is idempotent
- [ ] Test harness completes and reconstructed DICOM matches original (SHA verified)
- [ ] Encryption remains optional and does not break local development
- [ ] Files are saved under `sovereign_vault/pacs_data` and `sovereign_vault/pacs_compressed`

---

If you prefer, you can create the PR via the GitHub web UI by visiting the compare page:
`https://github.com/Roshan8005/RGAI-Sovereign-Matrix/compare/main...rgai/edge-pacs-chunking?expand=1`

Or using GitHub CLI (example):
```bash
gh pr create --base main --head rgai/edge-pacs-chunking --title "Edge PACS: chunked ternary compression + manifest + node unpacker (with test harness)" --body-file PR_BODY.md
```
