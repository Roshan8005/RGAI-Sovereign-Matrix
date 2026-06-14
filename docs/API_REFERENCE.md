# API Reference: RGAI Sovereign Matrix

The `discovery_server.py` exposes a RESTful API over HTTP (default port `5002`) for edge node registration, job ingestion, and telemetry monitoring.

---

## 1. Edge Node Orchestration

### `POST /register`
Registers a new edge node (phone, workstation) into the mesh network.

**Payload:**
```json
{
  "node_id": "phone-arm64-1",
  "port": 9999,
  "capital": 0.0,
  "public_key": "<hex_encoded_x25519_public_key>",
  "payload": {
    "cpu_load": 15.4,
    "ram_usage": 32.1
  }
}
```

**Response:**
Returns the network's active peers and the Discovery Server's public key (for cryptographic handshake).
```json
{
  "status": "registered",
  "peers": { ... },
  "server_public_key": "<hex_encoded_x25519_public_key>"
}
```

### `GET /peers`
Returns a JSON dictionary of all active peers that have pinged the server within the last 5 minutes. Nodes inactive for >300 seconds are automatically evicted.

---

## 2. Telemetry & Ledger Monitoring

### `GET /api/telemetry`
Returns an array of actively connected edge nodes, formatted for the React frontend dashboard.
```json
{
  "nodes": [
    {
      "id": "phone-arm64-1",
      "status": "online",
      "cpu_usage": 15.4,
      "ram_usage": 32.1,
      "vpn_ip": "192.168.1.104"
    }
  ]
}
```

### `GET /api/ledger`
Returns the complete immutable ledger containing all registered nodes and inference tasks.

---

## 3. Workload Ingestion

### `POST /api/v1/jobs/pacs`
Triggered by the `dicom_proxy_gateway.py` after a DICOM series has been intercepted and anonymized.

**Payload:**
```json
{
  "source": "DICOM_PROXY",
  "bytes": 10485760
}
```
**Response:**
```json
{
  "status": "accepted",
  "job_id": "PACS_JOB_1718300000"
}
```

### `POST /api/v1/jobs/inference`
Triggered when an external client pushes raw Tensor arrays directly to the matrix for distributed ONNX inference.

### `GET /api/v1/jobs/status/<job_id>`
Returns the real-time processing status of a specific inference or PACS job.

---

## 4. Bootstrapping & Model Distribution

These endpoints allow edge nodes to dynamically pull the required runtime scripts and inference models.

- `GET /bootstrap`: Returns the `bootstrap_termux.sh` script for Android devices.
- `GET /download/rgai_phone_node.py`: Serves the primary execution logic for edge inference.
- `GET /download/ternary_math_compressor.py`: Serves the Base-3 algorithm dependencies.
- `GET /models/<filename>`: Securely serves ONNX models (`.onnx`) required for clinical triage execution.
