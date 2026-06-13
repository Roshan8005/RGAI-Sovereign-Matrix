import asyncio
import os
import json
import time
import hashlib
import random
import urllib.request
import urllib.error
from mesh_crypto import MeshCrypto

DISCOVERY_SERVER_URL = "http://127.0.0.1:5002"
UDP_IP = "127.0.0.1" # Sending to localhost for the stress test
UDP_PORT = 9998 # The secure signaling port in router

# We'll share one cryptography setup logic across nodes
class AsyncMeshNode:
    def __init__(self, node_id):
        self.node_id = node_id
        # In memory crypto generation, we don't need a file for each of the 1000 nodes!
        self.crypto = MeshCrypto() 
        self.shared_secret_derived = False

    async def register_node(self):
        """Asynchronously register node to Discovery Server and derive shared secret."""
        # Run synchronous urllib request in thread pool
        def _do_register():
            req_payload = {
                "node_id": self.node_id,
                "ip": "127.0.0.1",
                "port": random.randint(10000, 60000),
                "public_key": self.crypto.get_public_bytes().hex()
            }
            req = urllib.request.Request(
                f"{DISCOVERY_SERVER_URL}/register",
                data=json.dumps(req_payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                res_data = json.loads(resp.read().decode('utf-8'))
                return res_data.get("server_public_key")

        try:
            server_pub_hex = await asyncio.to_thread(_do_register)
            if server_pub_hex:
                self.crypto.derive_shared_secret(bytes.fromhex(server_pub_hex))
                self.shared_secret_derived = True
                return True
        except Exception as e:
            # print(f"[{self.node_id}] Registration failed: {e}")
            pass
        return False

    def build_telemetry_packet(self, cycle_count):
        """Build the ChaCha20 encrypted payload."""
        payload = {
            "type": "heartbeat",
            "node_id": self.node_id,
            "status": "active",
            "cpu_load": round(random.uniform(5.0, 95.0), 2),
            "ram_usage": round(random.uniform(10.0, 90.0), 2),
            "battery_level": random.randint(10, 100),
            "cycle_count": cycle_count,
            "simulated_yield": round(random.uniform(0.001, 0.05), 5),
            "timestamp": time.time()
        }
        encoded_message = json.dumps(payload).encode('utf-8')
        encrypted_payload = self.crypto.encrypt(encoded_message)
        header = b"\xCF" + self.node_id.encode('utf-8').ljust(32, b'\0')
        return header + encrypted_payload


class SwarmUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport


async def run_swarm_batch(nodes, batch_index, protocol):
    """Run a batch of nodes sending telemetry."""
    cycle = 1
    while True:
        sent_count = 0
        for node in nodes:
            if node.shared_secret_derived:
                packet = node.build_telemetry_packet(cycle)
                protocol.transport.sendto(packet, (UDP_IP, UDP_PORT))
                sent_count += 1
                # Small yield to event loop to avoid locking thread entirely
                await asyncio.sleep(0)
        
        # print(f"[Batch {batch_index}] Transmitted {sent_count} packets for cycle {cycle}.")
        cycle += 1
        await asyncio.sleep(8) # Heartbeat interval


async def main():
    print("==========================================================")
    print(" [RGAI] 1,000-NODE CRUCIBLE STRESS TESTER")
    print("==========================================================")
    
    # 1. Setup global UDP socket for sending
    loop = asyncio.get_running_loop()
    import socket
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SwarmUDPProtocol(),
        remote_addr=None,
        family=socket.AF_INET
    )
    
    total_nodes = 1000
    batch_size = 100
    all_nodes = []
    active_tasks = []
    
    print(f"Target: {total_nodes} nodes, staggering in batches of {batch_size}.")
    
    for batch_idx in range(total_nodes // batch_size):
        start_id = batch_idx * batch_size + 1
        end_id = start_id + batch_size - 1
        print(f"\n>>> Bootstrapping Batch {batch_idx+1}: Nodes {start_id} to {end_id}...")
        
        # Create nodes
        batch_nodes = [AsyncMeshNode(f"SYNTHETIC_NODE_{i:04d}") for i in range(start_id, end_id + 1)]
        all_nodes.extend(batch_nodes)
        
        # Register nodes concurrently
        print(f"[Batch {batch_idx+1}] Registering {batch_size} identities with Discovery Server via HKDF...")
        reg_tasks = [asyncio.create_task(node.register_node()) for node in batch_nodes]
        results = await asyncio.gather(*reg_tasks)
        success_count = sum(1 for r in results if r)
        print(f"[Batch {batch_idx+1}] {success_count}/{batch_size} nodes successfully derived secrets.")
        
        if success_count == 0:
            print("[CRITICAL] 0 registrations succeeded. Discovery Server might be overwhelmed!")
        
        # Start heartbeat loop for this batch
        task = asyncio.create_task(run_swarm_batch(batch_nodes, batch_idx+1, protocol))
        active_tasks.append(task)
        
        # Stagger delay before next batch to map performance curve
        print(f"[Crucible] {len(all_nodes)} nodes now actively transmitting. Holding 5 seconds to map curve...")
        await asyncio.sleep(5)

    print("\n==========================================================")
    print(" [Crucible] ALL 1,000 NODES ACTIVE & TRANSMITTING")
    print(" Monitoring system... (Press Ctrl+C to abort)")
    print("==========================================================")
    
    try:
        while True:
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass
    finally:
        transport.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCrucible Terminated.")
