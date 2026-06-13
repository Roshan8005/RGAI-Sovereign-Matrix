import asyncio
import aiohttp
import time
import random

ORCHESTRATOR_URL = "http://127.0.0.1:8080"
TOTAL_NODES = 100
HEARTBEAT_INTERVAL = 2.0  # seconds

async def node_worker(session, node_index):
    node_id = f"MOBILE_NODE_{node_index:04d}"
    print(f"[{node_id}] Booting up...")
    
    # Base temperature around 35-40C
    current_temp = random.uniform(35.0, 40.0)
    
    while True:
        # Simulate slight temperature fluctuation
        current_temp += random.uniform(-0.5, 0.8)
        
        payload = {
            "node_id": node_id,
            "ip_address": f"192.168.1.{node_index}",
            "battery_temp": current_temp,
            "available_ram_mb": random.uniform(500, 2000)
        }
        
        try:
            async with session.post(f"{ORCHESTRATOR_URL}/heartbeat", json=payload, timeout=2) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    state = data.get("node_state")
                    if state == -1:
                        # Cooling down behavior
                        # print(f"[{node_id}] Orchestrator responded with -1 (Throttled). Cooling down...")
                        current_temp -= random.uniform(1.0, 2.0)
                else:
                    print(f"[{node_id}] Heartbeat error: {resp.status}")
        except Exception as e:
            # print(f"[{node_id}] Connection error: {e}")
            pass
            
        await asyncio.sleep(HEARTBEAT_INTERVAL)

async def monitor_metrics(session):
    while True:
        try:
            async with session.get(f"{ORCHESTRATOR_URL}/metrics", timeout=2) as resp:
                if resp.status == 200:
                    metrics = await resp.json()
                    print("\n--- [RGAI TELEMETRY SNAPSHOT] ---")
                    print(f"Active Nodes (state=1):   {metrics.get('active_nodes')}")
                    print(f"Throttled Nodes (state=-1): {metrics.get('offline_nodes')}")
                    print(f"Average Mesh Temp:        {metrics.get('average_node_temp_c')} °C")
                    print("---------------------------------\n")
        except Exception:
            pass
        await asyncio.sleep(5)

async def main():
    print("==========================================================")
    print(f" [RGAI] ORCHESTRATOR STRESS TESTER ({TOTAL_NODES} NODES)")
    print("==========================================================")
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(1, TOTAL_NODES + 1):
            tasks.append(asyncio.create_task(node_worker(session, i)))
            
        # Add the monitoring task
        tasks.append(asyncio.create_task(monitor_metrics(session)))
        
        # Wait indefinitely
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStress Test Terminated.")
