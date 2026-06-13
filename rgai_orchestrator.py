import sqlite3
import time
import threading
from typing import Optional, List
from flask import Flask, request, jsonify
from waitress import serve
from pydantic import BaseModel, Field, ValidationError

app = Flask(__name__)
DB_PATH = "orchestrator_ledger.db"

# ---------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------
class HeartbeatPayload(BaseModel):
    node_id: str
    ip_address: str
    battery_temp: float
    available_ram_mb: float

class TaskPayload(BaseModel):
    priority: int = Field(default=0, description="Higher number = higher priority")
    study_id: str
    fragment_data: str # Base64 encoded payload

class ResultPayload(BaseModel):
    node_id: str
    task_id: int
    result_data: str # Base64 encoded result

# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Pro-tip applied: Write-Ahead Logging for high concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                ip_address TEXT,
                state INTEGER,
                battery_temp REAL,
                available_ram_mb REAL,
                last_heartbeat REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                priority INTEGER DEFAULT 0,
                study_id TEXT,
                fragment_data TEXT,
                status TEXT, -- PENDING, ASSIGNED, COMPLETED, FAILED
                assigned_node TEXT,
                assigned_at REAL,
                result_data TEXT
            )
        """)
        # Create indexes for high-performance lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, priority DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_state ON nodes(state)")
    conn.close()

# ---------------------------------------------------------
# BACKGROUND WORKER: GRACEFUL DEGRADATION & RECOVERY
# ---------------------------------------------------------
def disaster_recovery_worker():
    """
    Runs in the background. Finds orphaned tasks or tasks assigned to 
    overheated nodes and instantly re-queues them.
    Also implements Dead Letter Queue logic (5-minute timeout).
    """
    while True:
        try:
            conn = get_db_connection()
            now = time.time()
            with conn:
                # 1. Heartbeat Timeout: Mark stale nodes as disconnected (-1) if no heartbeat for 30s
                conn.execute("""
                    UPDATE nodes 
                    SET state = -1 
                    WHERE state = 1 AND (? - last_heartbeat) > 30.0
                """, (now,))
                
                # 2. Find tasks assigned to dead/overheated nodes and re-queue them
                conn.execute("""
                    UPDATE tasks 
                    SET status = 'PENDING', assigned_node = NULL, assigned_at = NULL 
                    WHERE status = 'ASSIGNED' AND assigned_node IN (
                        SELECT node_id FROM nodes WHERE state = -1
                    )
                """)
                
                # 3. Dead Letter Queue: Tasks stuck in ASSIGNED for > 5 minutes (300s)
                conn.execute("""
                    UPDATE tasks 
                    SET status = 'PENDING', assigned_node = NULL, assigned_at = NULL 
                    WHERE status = 'ASSIGNED' AND (? - assigned_at) > 300.0
                """, (now,))
            conn.close()
        except Exception as e:
            print(f"[Orchestrator DR] Warning: {e}")
        time.sleep(1.0) # Run every second to manage RTO

# ---------------------------------------------------------
# API ENDPOINTS
# ---------------------------------------------------------
@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    try:
        data = HeartbeatPayload(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Invalid payload schema", "details": e.errors()}), 400

    # Thermal-Aware Scheduling Logic
    state = 1
    if data.battery_temp > 45.0:
        state = -1 # Node is throttling, mark as unavailable
        # Avoid printing repeatedly for 1000 nodes, but keep logic intact.

    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT INTO nodes (node_id, ip_address, state, battery_temp, available_ram_mb, last_heartbeat)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                ip_address = excluded.ip_address,
                state = excluded.state,
                battery_temp = excluded.battery_temp,
                available_ram_mb = excluded.available_ram_mb,
                last_heartbeat = excluded.last_heartbeat
        """, (data.node_id, data.ip_address, state, data.battery_temp, data.available_ram_mb, time.time()))
    conn.close()
    return jsonify({"status": "acknowledged", "node_state": state})

@app.route("/add_task", methods=["POST"])
def add_task():
    try:
        data = TaskPayload(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Invalid payload", "details": e.errors()}), 400

    conn = get_db_connection()
    with conn:
        cursor = conn.execute("""
            INSERT INTO tasks (priority, study_id, fragment_data, status)
            VALUES (?, ?, ?, 'PENDING')
        """, (data.priority, data.study_id, data.fragment_data))
        task_id = cursor.lastrowid
    conn.close()
    return jsonify({"task_id": task_id, "status": "PENDING"}), 201

@app.route("/pull_task", methods=["GET"])
def pull_task():
    node_id = request.args.get("node_id")
    if not node_id:
        return jsonify({"error": "node_id required"}), 400

    conn = get_db_connection()
    node = conn.execute("SELECT state FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
    if not node or node["state"] != 1:
        conn.close()
        return jsonify({"message": "Node is offline or overheating. Cannot assign task."}), 403

    task = conn.execute("""
        SELECT task_id, study_id, fragment_data 
        FROM tasks 
        WHERE status = 'PENDING' 
        ORDER BY priority DESC, task_id ASC 
        LIMIT 1
    """).fetchone()

    if task:
        with conn:
            conn.execute("""
                UPDATE tasks 
                SET status = 'ASSIGNED', assigned_node = ?, assigned_at = ? 
                WHERE task_id = ?
            """, (node_id, time.time(), task["task_id"]))
        conn.close()
        return jsonify(dict(task))
    else:
        conn.close()
        return jsonify({"message": "No pending tasks"}), 404

@app.route("/submit_result", methods=["POST"])
def submit_result():
    try:
        data = ResultPayload(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Invalid payload", "details": e.errors()}), 400

    conn = get_db_connection()
    with conn:
        res = conn.execute("""
            UPDATE tasks 
            SET status = 'COMPLETED', result_data = ? 
            WHERE task_id = ? AND assigned_node = ?
        """, (data.result_data, data.task_id, data.node_id))
        
        if res.rowcount == 0:
            conn.close()
            return jsonify({"error": "Task not found or assigned to different node"}), 400
            
    conn.close()
    return jsonify({"status": "success"})

@app.route("/metrics", methods=["GET"])
def metrics():
    """Telemetry Aggregation Endpoint"""
    conn = get_db_connection()
    
    active_nodes = conn.execute("SELECT COUNT(*) as count FROM nodes WHERE state = 1").fetchone()["count"]
    offline_nodes = conn.execute("SELECT COUNT(*) as count FROM nodes WHERE state = -1").fetchone()["count"]
    
    avg_temp_row = conn.execute("SELECT AVG(battery_temp) as avg_temp FROM nodes WHERE state = 1").fetchone()
    avg_temp = round(avg_temp_row["avg_temp"], 2) if avg_temp_row["avg_temp"] else 0.0

    pending_tasks = conn.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'PENDING'").fetchone()["count"]
    completed_tasks = conn.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'COMPLETED'").fetchone()["count"]
    
    conn.close()
    
    return jsonify({
        "active_nodes": active_nodes,
        "offline_nodes": offline_nodes,
        "average_node_temp_c": avg_temp,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks
    })

# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    print("==========================================================")
    print(" [RGAI] ORCHESTRATOR NODE INITIATING...")
    print("==========================================================")
    init_db()
    print("[+] Task Ledger initialized with WAL mode and Indexed Schema.")
    
    dr_thread = threading.Thread(target=disaster_recovery_worker, daemon=True)
    dr_thread.start()
    print("[+] Disaster Recovery Watchdog running.")
    print("[+] Starting Waitress WSGI Server on port 8080 (32 threads)...")
    
    # Waitress is production grade WSGI, suitable for handling concurrent node connections.
    serve(app, host="0.0.0.0", port=8080, threads=32)
