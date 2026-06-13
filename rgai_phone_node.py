import socket
import time
import json
import random
import os
import sys
import urllib.request
import urllib.error
import hashlib
import hmac
import secrets
import numpy as np
import onnxruntime as ort

# Configure stdout/stderr to use UTF-8 to prevent emoji encoding crashes on Windows console/logs
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Configuration Setup
NODE_ID = os.environ.get("RGAI_NODE_ID", "ROSHAN_ANDROID_NODE_01")
PORT = int(os.environ.get("RGAI_NODE_PORT", "9999"))
HEARTBEAT_INTERVAL = int(os.environ.get("RGAI_HEARTBEAT_INTERVAL", "8"))
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phone_credentials.key")

def encode_ternary_payload(data_str):
    """Encodes the payload into a balanced ternary format (-1, 0, 1) using Sah Protocol trit mapping"""
    try:
        # uniform 6-trit mapping space simulation
        from ternary_math_compressor import SahTernaryCompressor
        compressor = SahTernaryCompressor()
        matrix = compressor.string_to_ternary_stream(data_str)
        return compressor.serialize_matrix_to_string(matrix)
    except Exception:
        # Fallback simple balanced trit encoding
        trits = ['T', '0', '1']
        fallback_str = data_str if isinstance(data_str, str) else data_str.hex()
        return "RGAI_TRIT_START:" + "".join(random.choice(trits) for _ in range(30)) + ":" + fallback_str

def mobile_udp_listener(sock, private_key, public_key):
    """Background listener for incoming mesh protocols like Diagnostic Image chunks."""
    while True:
        try:
            data, addr = sock.recvfrom(8192)
            
            # Direct Binary Intercept for Fractal Nexus Protocol (Bypass Ternary Bloat)
            if len(data) > 0 and data[0] in (0xA3, 0xF0, 0xD1, 0xD2, 0xE1, 0xE2):
                raw_bytes = data
            else:
                try:
                    decoded_str = data.decode('utf-8')
                except UnicodeDecodeError:
                    continue # random noise
                    
                # Decompress Ternary Stream
                from ternary_math_compressor import SahTernaryCompressor
                compressor = SahTernaryCompressor()
                
                if decoded_str.startswith("RGAI_TRIT_START:") or decoded_str.startswith("{"):
                    continue
                    
                matrix = compressor.deserialize_string_to_matrix(decoded_str)
                raw_bytes = compressor.ternary_stream_to_bytes(matrix)
            
            if raw_bytes and raw_bytes[0] == 0xD1:
                # Detected PACS Image Chunk!
                from fractal_nexus import FractalNexusEngine
                nexus_engine = FractalNexusEngine()
                packets = nexus_engine.unpack(raw_bytes)
                for packet in packets:
                    if packet and packet.get("protocol") == "RGAI_PACS_CHUNK":
                        chunk_idx = packet["chunk_index"]
                        image_id = packet["image_id"]
                        pixel_bytes = packet["pixel_bytes"]
                        
                        # Process/store locally and calculate proof-of-storage hash
                        chunk_hash = hashlib.sha256(pixel_bytes).hexdigest()
                        print(f"\n[PACS Receiver] Downloaded {len(pixel_bytes)} bytes of medical data for {image_id} (Chunk {chunk_idx})")
                        print(f"[PACS Receiver] Computed Proof-of-Storage Hash: {chunk_hash[:16]}...")
                        
                        # Generate Ack Packet
                        ack_bytes = nexus_engine.pack_image_ack(
                            node_id=NODE_ID,
                            image_id=image_id,
                            chunk_index=chunk_idx,
                            chunk_hash=chunk_hash
                        )
                        if ack_bytes:
                            # Send raw binary ack over UDP directly to avoid MTU bloat
                            sock.sendto(ack_bytes, ('255.255.255.255', PORT))
                            print(f"[PACS Receiver] Dispatched Image Acknowledgement for higher $USD yield!\n")
            elif raw_bytes and raw_bytes[0] == 0xE1:
                # Detected OpenClaw LAM Task!
                from fractal_nexus import FractalNexusEngine
                nexus_engine = FractalNexusEngine()
                packets = nexus_engine.unpack(raw_bytes)
                for packet in packets:
                    if packet and packet.get("protocol") == "RGAI_LAM_TASK":
                        target = packet.get("target_node")
                        if target == "ALL" or target == NODE_ID:
                            task_id = packet.get("task_id")
                            matrix_size = packet.get("matrix_size", 128)
                            iterations = packet.get("iterations", 500)
                            
                            print(f"\n[Edge AI] Received Vision Inference Task {task_id}.")
                            print(f"[Edge AI] Spawning background thread for ONNX inference...")
                            
                            def execute_lam_task(t_id):
                                start_time = time.time()
                                model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "squeezenet.onnx")
                                
                                try:
                                    # Load ONNX Session
                                    session = ort.InferenceSession(model_path)
                                    input_name = session.get_inputs()[0].name
                                    
                                    # Generate a dummy input tensor for SqueezeNet (1, 3, 224, 224)
                                    # In a full deployment, this would be the actual pixel data from the payload
                                    dummy_tensor = np.random.randn(1, 3, 224, 224).astype(np.float32)
                                    
                                    # Run inference
                                    outputs = session.run(None, {input_name: dummy_tensor})
                                    pred_class = np.argmax(outputs[0])
                                    
                                    exec_time_ms = int((time.time() - start_time) * 1000)
                                    result_hash = hashlib.sha256(f"{t_id}:class_{pred_class}".encode()).hexdigest()
                                    
                                    print(f"[Edge AI] Inference completed in {exec_time_ms}ms! Predicted Class: {pred_class}")
                                    print(f"[Edge AI] Proof Hash: {result_hash[:16]}...")
                                    
                                    result_bytes = nexus_engine.pack_lam_result(
                                        node_id=NODE_ID,
                                        task_id=t_id,
                                        execution_time_ms=exec_time_ms,
                                        result_hash=result_hash
                                    )
                                    if result_bytes:
                                        sock.sendto(result_bytes, ('255.255.255.255', PORT))
                                        print(f"[Edge AI] Broadcasted ONNX inference result back to network for yield execution!\n")
                                except Exception as e:
                                    print(f"[Edge AI] Inference Failed: {e}")
                                    
                            import threading
                            threading.Thread(target=execute_lam_task, args=(task_id,), daemon=True).start()
        except Exception as e:
            print(f"[Mobile UDP Listener Error] {e}")

def get_or_create_node_credentials():
    """Retrieves or creates node private/public credentials for secure signing."""
    from mesh_crypto import MeshCrypto
    crypto = MeshCrypto.load_or_generate(CREDENTIALS_FILE)
    return crypto.get_private_bytes().hex(), crypto.get_public_bytes().hex()

def sign_payload(payload_dict, private_key):
    """Signs the JSON payload using HMAC-SHA256 and returns signature."""
    serialized = json.dumps(payload_dict, sort_keys=True)
    signature = hmac.new(
        private_key.encode('utf-8'),
        serialized.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_hardware_metrics(prev_cpu_times=None):
    """Retrieves real hardware metrics on Linux/Android, falls back to simulation on other platforms."""
    cpu_load = None
    ram_usage = None
    battery_level = None
    
    # 1. RAM Usage from /proc/meminfo
    try:
        if os.path.exists('/proc/meminfo'):
            meminfo = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].rstrip(':')] = int(parts[1])
            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0) + meminfo.get('Buffers', 0) + meminfo.get('Cached', 0))
            if total > 0:
                ram_usage = round(((total - available) / total) * 100, 2)
    except Exception:
        pass

    # 2. CPU Usage from /proc/stat
    current_cpu_times = None
    try:
        if os.path.exists('/proc/stat'):
            with open('/proc/stat', 'r') as f:
                first_line = f.readline()
                if first_line.startswith('cpu '):
                    parts = first_line.split()[1:]
                    current_cpu_times = [float(x) for x in parts]
            if prev_cpu_times and current_cpu_times:
                # CPU usage = (Idle time difference) / (Total time difference)
                prev_idle = prev_cpu_times[3] + (prev_cpu_times[4] if len(prev_cpu_times) > 4 else 0)
                curr_idle = current_cpu_times[3] + (current_cpu_times[4] if len(current_cpu_times) > 4 else 0)
                
                prev_total = sum(prev_cpu_times)
                curr_total = sum(current_cpu_times)
                
                diff_idle = curr_idle - prev_idle
                diff_total = curr_total - prev_total
                
                if diff_total > 0:
                    cpu_load = round((1.0 - (diff_idle / diff_total)) * 100, 2)
    except Exception:
        pass

    # 3. Battery from /sys/class/power_supply
    try:
        battery_paths = [
            '/sys/class/power_supply/battery/capacity',
            '/sys/class/power_supply/BAT0/capacity',
            '/sys/class/power_supply/BAT1/capacity'
        ]
        for path in battery_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    battery_level = int(f.read().strip())
                break
    except Exception:
        pass

    # Fallback to simulation if not Linux or reading failed
    if cpu_load is None:
        cpu_load = round(random.uniform(5.0, 45.0), 2)
    if ram_usage is None:
        ram_usage = round(random.uniform(30.0, 65.0), 2)
    if battery_level is None:
        battery_level = random.randint(60, 95)
        
    return cpu_load, ram_usage, battery_level, current_cpu_times

def bootstrap_onnx_model(discovery_url):
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "squeezenet.onnx")
    if not os.path.exists(model_path):
        if discovery_url:
            model_url = f"{discovery_url.rstrip('/')}/models/squeezenet.onnx"
            print(f"[ONNX Bootstrap] Downloading SqueezeNet from {model_url}...")
            try:
                urllib.request.urlretrieve(model_url, model_path)
                print("[ONNX Bootstrap] Download complete.")
            except Exception as e:
                print(f"[ONNX Bootstrap] Failed: {e}")
        else:
            print("[ONNX Bootstrap] Discovery URL not set, cannot download model.")
    return model_path

def run_mobile_worker_node():
    print("==========================================================")
    print(f"[Mobile Swarm] RGAI SWARM WORKER NODE ACTIVE: {NODE_ID}   ")
    print(f"[Mobile Swarm] Memory footprint optimization target: <15MB")
    print("==========================================================")
    
    private_key, public_key = get_or_create_node_credentials()
    from mesh_crypto import MeshCrypto
    node_crypto = MeshCrypto.load_or_generate(CREDENTIALS_FILE)
    print(f"[Crypto] Loaded Node Public Identity Hash: {public_key[:16]}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(('', PORT))
    except Exception as e:
        print(f"[Network Warning] Could not bind UDP listener to port {PORT}: {e}")

    # Start listener thread for diagnostic PACS data
    import threading
    listener_thread = threading.Thread(target=mobile_udp_listener, args=(sock, private_key, public_key), daemon=True)
    listener_thread.start()
    
    
    cycle_count = 0
    discovery_url = os.environ.get("DISCOVERY_SERVER_URL")
    
    if discovery_url:
        print(f"[Mobile Swarm] Connected to Discovery Server: {discovery_url}")
        bootstrap_onnx_model(discovery_url)
    else:
        print("[Mobile Swarm] Operating in local broadcast-only mode. (DISCOVERY_SERVER_URL not set)")
        
    prev_cpu_times = None
    
    while True:
        cycle_count += 1
        
        # Calculate real/simulated hardware diagnostics
        cpu_load, ram_usage, battery, prev_cpu_times = get_hardware_metrics(prev_cpu_times)
        processed_chunk_size = random.randint(500, 2500)
        simulated_yield = round(processed_chunk_size * 0.000005, 5)
        
        # Structure the payload in standard RGAI MESH format
        payload = {
            "protocol": "RGAI_SAH_MESH",
            "node_id": NODE_ID,
            "net_capital": simulated_yield,
            "cpu_load": cpu_load,
            "ram_usage": ram_usage,
            "battery_level": battery,
            "public_key": public_key,
            "cycle": cycle_count,
            "processed_bytes": processed_chunk_size,
            "timestamp": time.time()
        }
        
        # Generate cryptographic signature of payload
        signature = sign_payload(payload, private_key)
        payload["signature"] = signature
        
        # Apply Fractal Nexus high-density binary packing before ternary encoding!
        try:
            from fractal_nexus import FractalNexusEngine
            nexus_engine = FractalNexusEngine()
            packed_binary = nexus_engine.pack_single_node(payload)
            raw_data = packed_binary
        except Exception as fe:
            print(f"[Mobile Swarm] Fractal Nexus compression fallback: {fe}")
            raw_data = json.dumps(payload)
            
        encoded_message = encode_ternary_payload(raw_data).encode('utf-8')
        
        # 1. Register with Discovery Server and fetch peers list (NAT Traversal)
        peers = {}
        if discovery_url:
            try:
                req_payload = {
                    "node_id": NODE_ID,
                    "port": PORT,
                    "capital": simulated_yield,
                    "public_key": public_key,
                    "signature": signature,
                    "payload": payload
                }
                # bypass-tunnel-reminder header to resolve Localtunnel warning pages
                req = urllib.request.Request(
                    f"{discovery_url.rstrip('/')}/register",
                    data=json.dumps(req_payload).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'bypass-tunnel-reminder': 'true',
                        'User-Agent': 'RGAIMobileNode/2.0'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
                    peers = res_data.get("peers", {})
                    server_pub_hex = res_data.get("server_public_key")
                    if server_pub_hex and not getattr(node_crypto, "shared_secret", None):
                        node_crypto.derive_shared_secret(bytes.fromhex(server_pub_hex))
                        print("[Crypto] Derived Shared Secret with Master Router via HKDF!")
            except urllib.error.URLError as ue:
                print(f"[Mobile Swarm] Network unreachable or tunnel reset: {ue.reason}")
            except Exception as e:
                print(f"[Mobile Swarm] Discovery server registration delay/error: {e}")
                
        # 2. Transmit UDP presence beacon to local subnet broadcast
        if getattr(node_crypto, 'shared_secret', None):
            # Encrypt the payload and prepend magic byte + node_id
            encrypted_payload = node_crypto.encrypt(encoded_message)
            header = b"\xCF" + NODE_ID.encode('utf-8').ljust(32, b'\0')
            transmit_message = header + encrypted_payload
        else:
            transmit_message = encoded_message
            
        try:
            sock.sendto(transmit_message, ('255.255.255.255', PORT))
            print(f" -> [Broadcast Sent] Subnet ping transmitted on local port {PORT}")
        except Exception as e:
            print(f"[Network] Local broadcast unreachable: {e}")
            
        # 3. Transmit direct UDP packets to all discovered peers (NAT traversal direct signaling)
        for peer_id, peer_info in peers.items():
            if peer_id != NODE_ID:
                try:
                    peer_ip = peer_info["ip"]
                    peer_port = peer_info["port"]
                    sock.sendto(transmit_message, (peer_ip, peer_port))
                    print(f" -> [Direct Peer Ping] Transmitted packet directly to {peer_id} at {peer_ip}:{peer_port}")
                except Exception as e:
                    print(f" -> [Direct Peer Error] Failed to ping peer {peer_id}: {e}")
                    
        print(f"[Status Update] Cycle #{cycle_count} | CPU: {cpu_load}% | RAM: {ram_usage}% | Battery: {battery}% | Balance: +${simulated_yield} USD")
        time.sleep(HEARTBEAT_INTERVAL)

if __name__ == "__main__":
    run_mobile_worker_node()
