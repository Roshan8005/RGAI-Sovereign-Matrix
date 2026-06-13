from flask import Flask, request, jsonify, Response, send_from_directory
import time
import os
import local_ledger
from mesh_crypto import MeshCrypto

app = Flask(__name__)

# Initialize the Router's Master Keypair (shared between discovery & router via disk)
router_crypto = MeshCrypto.load_or_generate(os.path.join(os.path.dirname(__file__), "router_credentials.key"))

# In-memory ledger of active nodes
active_nodes = {}

# Locate directory of scripts dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,bypass-tunnel-reminder'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

@app.route('/register', methods=['POST', 'OPTIONS'])
def register_node():
    if request.method == 'OPTIONS':
        return Response(status=200)
        
    data = request.json or {}
    node_id = data.get('node_id')
    if not node_id:
        return jsonify({"error": "node_id is required"}), 400
        
    public_ip = request.remote_addr 
    local_port = data.get('port', 9999)
    capital = data.get('capital', 0.0)
    public_key = data.get('public_key', 'UNKNOWN')
    
    # Extract telemetry metrics
    payload = data.get('payload', {})
    cpu_load = payload.get('cpu_load', data.get('cpu_load', 0.0))
    ram_usage = payload.get('ram_usage', data.get('ram_usage', 0.0))
    
    # Store metrics sent by the node
    active_nodes[node_id] = {
        'ip': public_ip,
        'port': local_port,
        'capital': capital,
        'public_key': public_key,
        'cpu_load': cpu_load,
        'ram_usage': ram_usage,
        'last_seen': time.time()
    }
    
    # Note: In a production mesh, we would verify data['signature'] here using data['public_key']
    
    import json
    with open(os.path.join(BASE_DIR, "active_nodes.json"), "w") as f:
        json.dump(active_nodes, f)
        
    return jsonify({
        "status": "registered", 
        "peers": get_active_peers(),
        "server_public_key": router_crypto.get_public_bytes().hex()
    })

def get_active_peers():
    current_time = time.time()
    # Clean up nodes inactive for more than 5 minutes
    stale_nodes = [n for n, data in list(active_nodes.items()) if current_time - data['last_seen'] > 300]
    for n in stale_nodes:
        del active_nodes[n]
    return active_nodes

@app.route('/peers', methods=['GET'])
def get_peers():
    return jsonify({"peers": get_active_peers()})

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    formatted_nodes = []
    current_time = time.time()
    
    # Clean up stale nodes and format active ones
    for node_id, data in list(active_nodes.items()):
        if current_time - data['last_seen'] <= 300:
            formatted_nodes.append({
                "id": node_id,
                "status": "online",
                "cpu_usage": data.get('cpu_load', 20.0),
                "ram_usage": data.get('ram_usage', 40.0),
                "vpn_ip": data.get('ip', '127.0.0.1')
            })
        else:
            del active_nodes[node_id]
            
    # Include some mock nodes for visual verification if registry is empty
    if not formatted_nodes:
        formatted_nodes = [
            {"id": "node-mock-1", "status": "online", "cpu_usage": 15.4, "ram_usage": 35.2, "vpn_ip": "100.64.0.1"},
            {"id": "node-mock-2", "status": "online", "cpu_usage": 42.1, "ram_usage": 52.8, "vpn_ip": "100.64.0.2"}
        ]
        
    return jsonify({"nodes": formatted_nodes})

@app.route('/api/ledger', methods=['GET'])
def get_ledger():
    try:
        nodes = local_ledger.get_nodes()
        tasks = local_ledger.get_tasks()
        return jsonify({
            "nodes": nodes,
            "tasks": tasks
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/bootstrap', methods=['GET'])
def get_bootstrap_script():
    bootstrap_path = os.path.join(BASE_DIR, "bootstrap_termux.sh")
    if os.path.exists(bootstrap_path):
        with open(bootstrap_path, 'r', encoding='utf-8') as f:
            code = f.read()
        return Response(code, mimetype='text/x-shellscript')
    return Response("Bootstrap script not found", status=404)

@app.route('/models/<path:filename>', methods=['GET'])
def serve_model(filename):
    """Serves ONNX models securely for centralized bootstrapping by edge nodes."""
    models_dir = os.path.join(BASE_DIR, "models")
    return send_from_directory(models_dir, filename)

@app.route('/download/rgai_phone_node.py', methods=['GET'])
def get_phone_node_script():
    path = os.path.join(BASE_DIR, "rgai_phone_node.py")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        return Response(code, mimetype='text/plain')
    return Response("rgai_phone_node.py not found", status=404)

@app.route('/download/ternary_math_compressor.py', methods=['GET'])
def get_compressor_script():
    path = os.path.join(BASE_DIR, "ternary_math_compressor.py")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        return Response(code, mimetype='text/plain')
    return Response("ternary_math_compressor.py not found", status=404)

@app.route('/api/v1/jobs/pacs', methods=['POST'])
def ingest_pacs_job():
    """Accepts full-scale medical image series and proxy them to the UDP mesh."""
    # In a full implementation, this would parse a multipart DICOM block, slice it, 
    # and broadcast via Fractal Nexus on UDP 9999.
    # For now, it registers the job intent in the ledger.
    job_id = f"PACS_JOB_{int(time.time())}"
    local_ledger.add_task(
        task_id=job_id,
        goal="Ingest PACS DICOM Series",
        executor_id="Pending",
        status="Pending",
        payout=0.150
    )
    return jsonify({"status": "accepted", "job_id": job_id})

@app.route('/api/v1/jobs/inference', methods=['POST'])
def ingest_inference_job():
    """Accepts JSON Tensor Array for ONNX distribution."""
    job_id = f"INF_JOB_{int(time.time())}"
    local_ledger.add_task(
        task_id=job_id,
        goal="External Edge Inference Task",
        executor_id="Pending",
        status="Pending",
        payout=0.080
    )
    return jsonify({"status": "accepted", "job_id": job_id})

@app.route('/api/v1/jobs/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Returns real-time ledger verification breakdown."""
    tasks = local_ledger.get_tasks()
    for task in tasks:
        if task['task_id'] == job_id:
            return jsonify({"job_id": job_id, "status": task['status'], "executor": task['executor_id']})
    return jsonify({"error": "Job not found"}), 404

if __name__ == '__main__':
    from waitress import serve
    print("[RGAI] Discovery Server running on Waitress WSGI. Listening on 0.0.0.0:5002")
    serve(app, host='0.0.0.0', port=5002, threads=100)
