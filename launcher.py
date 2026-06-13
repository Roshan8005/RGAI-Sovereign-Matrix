import threading
import time
import os
import sys
import json

# Configure stdout/stderr to use UTF-8 to prevent emoji encoding crashes on Windows console/logs
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import ternary_mesh_router

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)
sys.path.append(BASE_DIR)

def start_node_engine():
    from node_engine import RGAIGrandUnifiedCore
    Engine = RGAIGrandUnifiedCore()
    Engine.start_unified_matrix()

def start_web_server():
    from server_core import app
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def run_github_bounty_loop():
    """Har 30 seconds me live GitHub endpoints check karne ka process loop"""
    from github_bounty_agent import execute_bounty_processing
    print("[Launcher] Spin-up: RGAI GitHub Interface Monitor Activated...")
    while True:
        try:
            execute_bounty_processing()
            time.sleep(30) # 30 seconds sync window interval
        except Exception as e:
            print(f"[Error] Bounty worker state exception: {e}")
            time.sleep(10)

def start_mesh_router():
    """Ternary Peer Mesh Discovery Thread execution"""
    print("[Launcher] Spin-up: Ternary Peer Discovery UDP Network active on Port 9999...")
    # Initialize global instance for access across web server processes
    ternary_mesh_router.global_router_instance = ternary_mesh_router.TernaryMeshRouter()
    
    # Start UDP listener thread
    listener_thread = threading.Thread(target=ternary_mesh_router.global_router_instance.listen_for_peers, daemon=True)
    listener_thread.start()
    
    # Periodic broadcast loop
    while True:
        try:
            # Fetch current balance dynamically to broadcast accurate token metric
            user_balance = 0.0
            user_file = os.path.join(BASE_DIR, "network_users", "roshan_sah_node.json")
            if os.path.exists(user_file):
                with open(user_file, 'r') as f:
                    data = json.load(f)
                    user_balance = data.get("user_ledger", {}).get("balance_usd", 0.0)
            
            ternary_mesh_router.global_router_instance.broadcast_presence("Roshan_Sah_Primary_Core", user_balance)
            time.sleep(10) # 10s mesh signaling beacon
        except Exception as e:
            print(f"[Error] Mesh broadcast heartbeat anomaly: {e}")
            time.sleep(5)

def start_globalos_kernel():
    """Starts the GlobalOS Core Runtime Daemon and initializes the SQLite ledger."""
    print("[Launcher] Spin-up: GlobalOS local-first distributed AI kernel initializing...")
    from local_ledger import initialize_database
    initialize_database()
    
    from globalos_kernel import GlobalOSKernel
    kernel = GlobalOSKernel("Node_Primary_Roshan")
    kernel.start_kernel()
    
    while True:
        time.sleep(1)

if __name__ == "__main__":
    print("==========================================================")
    print("       RGAI COGNITIVE MULTI-AGENT SWARM SYSTEM            ")
    print("==========================================================")
    
    t1 = threading.Thread(target=start_node_engine, daemon=True)
    t2 = threading.Thread(target=start_web_server, daemon=True)
    t3 = threading.Thread(target=run_github_bounty_loop, daemon=True)
    t4 = threading.Thread(target=start_mesh_router, daemon=True)
    t5 = threading.Thread(target=start_globalos_kernel, daemon=True)
    
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Launcher] Swarm deactivated securely.")

