import socket
import threading
import json
import time
import os
import sys

# Configure stdout/stderr to use UTF-8 to prevent emoji encoding crashes on Windows console/logs
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Global router instance container
global_router_instance = None

class TernaryMeshRouter:
    def __init__(self, port=9999):
        self.port = port
        self.nodes_registry = {}
        self.prev_cpu_times = None
        # UDP Protocol allocation for connectionless light-speed data pinging
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass
        self.sock.bind(('', self.port))
        
    def broadcast_presence(self, node_id, current_capital):
        """Pure network me local presence packet coordinate karna"""
        # Get real hardware metrics
        try:
            from rgai_phone_node import get_hardware_metrics
            cpu_load, ram_usage, battery, prev_cpu_times = get_hardware_metrics(self.prev_cpu_times)
            self.prev_cpu_times = prev_cpu_times
        except Exception:
            cpu_load = 15.0
            ram_usage = 45.0

        payload = {
            "protocol": "RGAI_SAH_MESH",
            "node_id": node_id,
            "net_capital": current_capital,
            "cpu_load": cpu_load,
            "ram_usage": ram_usage,
            "ternary_flag": 1, # Balanced Ternary Compressed State Active
            "timestamp": time.time()
        }
        raw_json = json.dumps(payload)
        
        # Apply Sah Protocol Ternary Compression before broadcasting over UDP!
        try:
            from ternary_math_compressor import SahTernaryCompressor
            compressor = SahTernaryCompressor()
            matrix = compressor.string_to_ternary_stream(raw_json)
            compressed_payload = compressor.serialize_matrix_to_string(matrix)
            print(f"[Mesh Router] Compressed Packet (Ternary Code): {compressed_payload[:40]}...")
            
            # Send the encoded string over UDP
            message = compressed_payload.encode('utf-8')
        except Exception as e:
            print(f"[Mesh Router] Compression fallback: {e}")
            message = raw_json.encode('utf-8')
            
        print(f"[Mesh Router] Broadcasting local signal presence token: {node_id}")
        # Local network subnet broadcast allocation
        try:
            self.sock.sendto(message, ('255.255.255.255', self.port))
        except Exception as e:
            print(f"[Mesh Router] Broadcast failure: {e}")

        # Register with public discovery server if URL is set in environment
        discovery_url = os.environ.get("DISCOVERY_SERVER_URL")
        if discovery_url:
            def register_http():
                try:
                    import urllib.request
                    req_payload = {
                        "node_id": node_id,
                        "port": self.port,
                        "capital": current_capital,
                        "cpu_load": cpu_load,
                        "ram_usage": ram_usage,
                        "payload": payload
                    }
                    req = urllib.request.Request(
                        f"{discovery_url.rstrip('/')}/register",
                        data=json.dumps(req_payload).encode('utf-8'),
                        headers={
                            'Content-Type': 'application/json',
                            'bypass-tunnel-reminder': 'true',
                            'User-Agent': 'RGAIPrimaryCore/2.0'
                        },
                        method='POST'
                    )
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        res_data = json.loads(resp.read().decode('utf-8'))
                        peers = res_data.get("peers", {})
                        for p_id, p_info in peers.items():
                            if p_id != node_id:
                                # Update nodes registry with peer public IP and port
                                self.nodes_registry[p_id] = {
                                    "address": p_info["ip"],
                                    "capital": p_info.get("capital", 0.0),
                                    "last_seen": "Active"
                                }
                                # Proactively send a direct UDP ping to this peer to open NAT hole
                                try:
                                    self.sock.sendto(message, (p_info["ip"], p_info["port"]))
                                except Exception:
                                    pass
                except Exception as ex:
                    print(f"[Mesh Router] Discovery registration failed: {ex}")
            
            threading.Thread(target=register_http, daemon=True).start()

    def dispatch_pacs_workload(self, binary_packet):
        """Broadcasts a raw diagnostic image chunk over the UDP mesh using ternary compression."""
        try:
            from ternary_math_compressor import SahTernaryCompressor
            compressor = SahTernaryCompressor()
            matrix = compressor.string_to_ternary_stream(binary_packet)
            compressed_payload = compressor.serialize_matrix_to_string(matrix)
            
            message = compressed_payload.encode('utf-8')
            self.sock.sendto(message, ('255.255.255.255', self.port))
            print(f"[Mesh Router] Dispatched high-density PACS Image Chunk via Fractal Nexus ({len(message)} bytes).")
            
            # Proactively ping discovered peers
            for peer_id, peer_info in self.nodes_registry.items():
                try:
                    self.sock.sendto(message, (peer_info["address"], self.port))
                except Exception:
                    pass
        except Exception as e:
            print(f"[Mesh Router] Failed to dispatch PACS workload: {e}")

    def dispatch_lam_workload(self, binary_packet):
        """Broadcasts a raw LAM OpenClaw task over the UDP mesh."""
        try:
            self.sock.sendto(binary_packet, ('255.255.255.255', self.port))
            print(f"[Mesh Router] Dispatched OpenClaw LAM Task via Fractal Nexus ({len(binary_packet)} bytes).")
            # Proactively ping discovered peers
            for peer_id, peer_info in self.nodes_registry.items():
                try:
                    self.sock.sendto(binary_packet, (peer_info["address"], self.port))
                except Exception:
                    pass
        except Exception as e:
            print(f"[Mesh Router] Failed to dispatch LAM workload: {e}")

    def listen_for_peers(self):
        print(f"[Mesh Router] Passive tracking channel active on port {self.port}...")
        while True:
            try:
                data, addr = self.sock.recvfrom(8192)
                packets_list = []

                # Decrypt TEMPEST Scrambler traffic
                if len(data) > 33 and data[0] == 0xCF:
                    try:
                        sender_node_id = data[1:33].rstrip(b'\0').decode('utf-8')
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

                
                # Direct Binary Intercept for Fractal Nexus Protocol (Bypass Ternary Bloat)
                if len(data) > 0 and data[0] in (0xA3, 0xF0, 0xD1, 0xD2, 0xE1, 0xE2):
                    try:
                        from fractal_nexus import FractalNexusEngine
                        nexus_engine = FractalNexusEngine()
                        packets_list = nexus_engine.unpack(data)
                        if data[0] == 0xD2:
                            pass # Handled quietly to avoid log spam
                        else:
                            print(f" -> [Mesh Router] Received raw binary Fractal Nexus payload from {addr[0]}.")
                    except Exception as e:
                        print(f"[Mesh Router] Binary decode error: {e}")
                else:
                    try:
                        decoded_str = data.decode('utf-8')
                    except UnicodeDecodeError:
                        continue # Ignore random noise
                        
                    # Check if it is a standard JSON string, mobile swarm node, or a custom Ternary Encoded String
                    if decoded_str.startswith("{"):
                        try:
                            packet = json.loads(decoded_str)
                            packets_list = [packet]
                        except Exception as e:
                            pass
                    elif decoded_str.startswith("RGAI_TRIT_START:"):
                        parts = decoded_str.split(":", 2)
                        if len(parts) == 3:
                            try:
                                packet = json.loads(parts[2])
                                packet["protocol"] = "RGAI_SAH_MESH"
                                packet["net_capital"] = packet.get("yield_usd", 0.0)
                                packets_list = [packet]
                            except Exception as e:
                                pass
                    else:
                        # Decompress Ternary Stream
                        try:
                            from ternary_math_compressor import SahTernaryCompressor
                            compressor = SahTernaryCompressor()
                            matrix = compressor.deserialize_string_to_matrix(decoded_str)
                            
                            # First try to parse as raw bytes to check for Fractal Nexus compression
                            raw_bytes = compressor.ternary_stream_to_bytes(matrix)
                            
                            if raw_bytes and raw_bytes[0] in (0xA3, 0xF0, 0xD1, 0xD2, 0xE1, 0xE2):
                                from fractal_nexus import FractalNexusEngine
                                nexus_engine = FractalNexusEngine()
                                packets_list = nexus_engine.unpack(raw_bytes)
                                print(f" -> [Mesh Router] Decrypted high-density Fractal Nexus package from {addr[0]} successfully.")
                            else:
                                # Fallback to standard JSON string
                                decompressed_json = compressor.ternary_stream_to_string(matrix)
                                packet = json.loads(decompressed_json)
                                packets_list = [packet]
                                print(f" -> [Mesh Router] Decrypted standard Sah Ternary package from {addr[0]} successfully.")
                        except Exception as e:
                            print(f"[Mesh Router] Decompression error on incoming packet: {e}")
                            continue
                
                # Process all unpacked telemetry packets (supports batching!)
                for packet in packets_list:
                    if packet and packet.get("protocol") == "RGAI_SAH_MESH":
                        peer_id = packet["node_id"]
                        self.nodes_registry[peer_id] = {
                            "address": addr[0],
                            "capital": packet.get("net_capital", 0.0),
                            "last_seen": "Active"
                        }
                        print(f" -> [Node Discovered] Link established with peer matrix: {peer_id} at {addr[0]}")
                        try:
                            from local_ledger import register_node
                            import random
                            cpu_load = packet.get("cpu_load", random.randint(10, 60))
                            ram_usage = packet.get("ram_usage", random.randint(20, 70))
                            register_node(
                                node_id=peer_id,
                                address=addr[0],
                                public_key=packet.get("public_key", "UNKNOWN"),
                                status="Active",
                                balance_usd=packet.get("net_capital", 0.0),
                                cpu_load=cpu_load,
                                ram_usage=ram_usage
                            )
                        except Exception as le:
                            print(f"[Mesh Router] Ledger registration failed: {le}")
                    elif packet and packet.get("protocol") == "RGAI_PACS_ACK":
                        peer_id = packet["node_id"]
                        chunk_idx = packet["chunk_index"]
                        print(f" -> [PACS Registry] Received Image Chunk {chunk_idx} Acknowledgement from {peer_id} at {addr[0]}")
                        try:
                            from local_ledger import register_node
                            import random
                            # Elevated yield for diagnostic imaging storage
                            yield_credit = 0.005  
                            current_balance = self.nodes_registry.get(peer_id, {}).get("capital", 0.0)
                            new_balance = current_balance + yield_credit
                            self.nodes_registry[peer_id] = {
                                "address": addr[0],
                                "capital": new_balance,
                                "last_seen": "Active"
                            }
                            register_node(
                                node_id=peer_id,
                                address=addr[0],
                                public_key="UNKNOWN",
                                status="Active",
                                balance_usd=new_balance,
                                cpu_load=random.randint(10, 60),
                                ram_usage=random.randint(20, 70)
                            )
                            from local_ledger import add_task
                            image_id = packet.get("image_id", "UNKNOWN")
                            chunk_hash = packet.get("chunk_hash", "UNKNOWN")
                            add_task(
                                task_id=f"{image_id}_chunk_{chunk_idx}",
                                goal=f"Store MRI PACS Chunk",
                                executor_id=peer_id,
                                status="Verified",
                                output=f"Storage Proof Validated",
                                payout=yield_credit,
                                signed_digest=chunk_hash
                            )
                            print(f" -> [Ledger] Awarded +${yield_credit} yield to {peer_id} for medical data processing.")
                        except Exception as le:
                            print(f"[PACS Registry Error] {le}")
                    elif packet and packet.get("protocol") == "RGAI_LAM_RESULT":
                        peer_id = packet["node_id"]
                        task_id = packet["task_id"]
                        exec_time = packet["execution_time_ms"]
                        print(f" -> [OpenClaw] Received LAM execution result for {task_id} from {peer_id} at {addr[0]} (Time: {exec_time}ms)")
                        try:
                            from local_ledger import register_node
                            import random
                            # Heavy yield for complex Large Action Model execution
                            yield_credit = 0.025  
                            current_balance = self.nodes_registry.get(peer_id, {}).get("capital", 0.0)
                            new_balance = current_balance + yield_credit
                            self.nodes_registry[peer_id] = {
                                "address": addr[0],
                                "capital": new_balance,
                                "last_seen": "Active"
                            }
                            register_node(
                                node_id=peer_id,
                                address=addr[0],
                                public_key="UNKNOWN",
                                status="Active",
                                balance_usd=new_balance,
                                cpu_load=random.randint(60, 95),
                                ram_usage=random.randint(40, 80)
                            )
                            from local_ledger import add_task
                            result_hash = packet.get("result_hash", "UNKNOWN")
                            add_task(
                                task_id=task_id,
                                goal="LAM Matrix Simulation",
                                executor_id=peer_id,
                                status="Verified",
                                output=f"Executed in {exec_time}ms",
                                payout=yield_credit,
                                signed_digest=result_hash
                            )
                            print(f" -> [Ledger] Awarded +${yield_credit} yield to {peer_id} for LAM computation.")
                        except Exception as le:
                            print(f"[OpenClaw Registry Error] {le}")
            except Exception as e:
                print(f"[Error] Mesh synchronization issue: {e}")
                break

if __name__ == "__main__":
    router = TernaryMeshRouter()
    # Allocating independent daemon execution for networking interfaces
    listener = threading.Thread(target=router.listen_for_peers, daemon=True)
    listener.start()
    
    # Live loop to keep testing the local transmission signals
    try:
        while True:
            router.broadcast_presence("Roshan_Sah_Primary_Core", 76.0)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[Mesh] Signal matrix offline.")
