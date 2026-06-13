import os
import sys
import time
import socket
import threading
import json
from local_ledger import register_node, add_task, get_tasks, enqueue_message, get_pending_messages, mark_message_sent
from mesh_protocol import SahSecureMeshProtocol
from agent_orchestrator import SahAgentOrchestrator

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class GlobalOSKernel:
    def __init__(self, node_id, port=9998):
        self.node_id = node_id
        self.port = port
        self.running = True
        
        # Initialize Cryptographic Mesh and Orchestration Engines
        self.secure_protocol = SahSecureMeshProtocol(node_id)
        self.orchestrator = SahAgentOrchestrator(node_id)
        
        # Configure local socket listener for secure signal coordinates
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.sock.bind(('', self.port))
            print(f"[GlobalOS Core] Secure signaling port bound at UDP Port {self.port}")
        except Exception as e:
            print(f"[GlobalOS Core] Port bind anomaly: {e}. Running in passive/secondary mode.")

    def run_telemetry_loop(self):
        """
        Periodically calculates system affinity metrics and updates 
        the local SQLite nodes registry.
        """
        print("[GlobalOS Core] Spawning Background Hardware Telemetry Daemon...")
        while self.running:
            try:
                # Retrieve current compute affinity metrics
                affinity_score = self.orchestrator.estimate_affinity_metrics() if hasattr(self.orchestrator, 'estimate_affinity_metrics') else self.orchestrator.estimate_hardware_affinity()
                
                # Mock CPU/RAM components for raw display
                cpu_load = round((1.0 - affinity_score) * 100.0, 2)
                ram_usage = round(45.0 + (cpu_load * 0.1), 2)
                
                # Register/Update local ledger coordinates
                register_node(
                    node_id=self.node_id,
                    address="127.0.0.1",
                    public_key=str(self.secure_protocol.public_key),
                    status="Active",
                    balance_usd=0.0,
                    cpu_load=cpu_load,
                    ram_usage=ram_usage
                )
            except Exception as e:
                print(f"[Telemetry Error] Telemetry loop fault: {e}")
            time.sleep(5)

    def run_mesh_listener(self):
        """
        Passive listener loop. Processes incoming encrypted mesh tasks, 
        evaluates credentials, decodes ternary matrices, and returns results.
        """
        print("[GlobalOS Core] Passive secure P2P listener active...")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                raw_envelope = data.decode('utf-8')
                
                # Check for GlobalOS broadcast envelopes
                if "payload_matrix" in raw_envelope and "sender_pubkey" in raw_envelope:
                    # Deserialize and decrypt the incoming task packet using secure DH protocol
                    decrypted_packet = self.secure_protocol.deserialize_secure_packet(raw_envelope)
                    
                    if decrypted_packet:
                        sender = decrypted_packet["sender_id"]
                        content = json.loads(decrypted_packet["payload"])
                        
                        # Process Task Delegation requests
                        if content.get("type") == "TASK_DELEGATION":
                            task_id = content["task_id"]
                            task_goal = content["goal"]
                            print(f"\n[GlobalOS Core] Received Delegated Task from Peer '{sender}': {task_goal}")
                            
                            # Execute the AI task using local SLM or rule-engine fallback
                            print(f"[GlobalOS Core] Allocating computational thread for Task {task_id}...")
                            add_task(task_id, task_goal, executor_id=self.node_id, status="In Progress")
                            
                            result_text = self.orchestrator.trigger_local_slm_inference(task_goal)
                            
                            # Mark task completed in database
                            add_task(task_id, task_goal, executor_id=self.node_id, status="Completed", output=result_text)
                            
                            # Prepare and send return envelope (encrypt with sender's public key)
                            result_payload = {
                                "type": "TASK_RESULT",
                                "task_id": task_id,
                                "output": result_text
                            }
                            sender_pubkey = int(content["sender_pubkey"])
                            
                            # Serialize and broadcast back the result
                            outbound_envelope = self.secure_protocol.serialize_secure_packet(
                                json.dumps(result_payload), sender_pubkey
                            )
                            if outbound_envelope:
                                self.sock.sendto(outbound_envelope.encode('utf-8'), ('255.255.255.255', self.port))
                                print(f"[GlobalOS Core] Secure task result returned successfully to peer: '{sender}'")
                                
                        elif content.get("type") == "TASK_RESULT":
                            task_id = content["task_id"]
                            task_output = content["output"]
                            print(f"\n[GlobalOS Core] Received Signed Task Result for {task_id} from Executor '{sender}'!")
                            
                            # Update local database with results
                            add_task(task_id, "Mesh Delegated Task Goal", executor_id=sender, status="Completed", output=task_output)
            except Exception as e:
                if not self.running:
                    break
                print(f"[Listener Error] Passive mesh thread error: {e}")
                time.sleep(2)

    def delegate_task_to_mesh(self, task_id, goal, peer_public_key, peer_id):
        """
        Packages a task into a secure encrypted packet and enqueues it 
        for transmission across the P2P broadcast matrix.
        """
        payload = {
            "type": "TASK_DELEGATION",
            "task_id": task_id,
            "goal": goal,
            "sender_pubkey": str(self.secure_protocol.public_key)
        }
        
        # Encrypt and serialize to base-3 state envelope
        envelope = self.secure_protocol.serialize_secure_packet(json.dumps(payload), peer_public_key)
        
        if envelope:
            # Add to offline ledger buffer queue
            enqueue_message(task_id, self.node_id, peer_id, "ENCRYPTED_AEAD", envelope)
            print(f"[GlobalOS Core] Enqueued secure task {task_id} delegation to '{peer_id}'.")
            
            # Immediately attempt to push queue to subnet
            self.flush_outbound_queue()

    def flush_outbound_queue(self):
        """Offline-resilience loop: Flushes queued pending messages over UDP socket."""
        pending = get_pending_messages()
        if not pending:
            return
            
        print(f"[GlobalOS Core] Processing outbound offline-queue buffer ({len(pending)} pending messages)...")
        for msg in pending:
            try:
                envelope = msg["ternary_encoded"]
                self.sock.sendto(envelope.encode('utf-8'), ('255.255.255.255', self.port))
                mark_message_sent(msg["msg_id"])
                print(f" -> Outbound Message {msg['msg_id']} sent successfully over physical broadcast subnet!")
            except Exception as e:
                print(f" -> Outbound transmission delayed (Adapter isolated): {e}. Kept in local buffer.")
                break

    def start_kernel(self):
        # Spawning independent daemon processing threads for absolute portability
        t1 = threading.Thread(target=self.run_telemetry_loop, daemon=True)
        t2 = threading.Thread(target=self.run_mesh_listener, daemon=True)
        
        t1.start()
        t2.start()
        
        # Flush queue thread
        def queue_flusher():
            while self.running:
                self.flush_outbound_queue()
                time.sleep(10)
        t3 = threading.Thread(target=queue_flusher, daemon=True)
        t3.start()

if __name__ == "__main__":
    kernel = GlobalOSKernel("Master_Sovereign_Roshan")
    kernel.start_kernel()
    
    # Simulate a local run loop
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        kernel.running = False
        print("\n[GlobalOS Core] Operational systems shutdown secured.")
