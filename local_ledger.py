import os
import sys
import sqlite3
import time

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "local_ledger.db")

def get_db_connection():
    """Returns a SQLite connection with dict factory for easy JSON mapping."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Creates local-first ledger schemas for offline-resilient node syncing."""
    print(f"[Ledger DB] Initializing Local SQLite Ledger at: {DB_PATH}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 🏛️ Nodes Registry Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nodes_registry (
        node_id TEXT PRIMARY KEY,
        address TEXT,
        public_key TEXT,
        status TEXT,
        balance_usd REAL,
        last_seen REAL,
        cpu_load REAL,
        ram_usage REAL
    )
    """)
    
    # 📋 Distributed Task Ledger Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_ledger (
        task_id TEXT PRIMARY KEY,
        goal TEXT,
        executor_id TEXT,
        status TEXT,
        output TEXT,
        payout REAL,
        created_at REAL,
        signed_digest TEXT
    )
    """)
    
    # 🛡️ Outbound Network Messages Queue Table (Offline resilience storage)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_messages (
        msg_id TEXT PRIMARY KEY,
        sender TEXT,
        recipient TEXT,
        encrypted_payload TEXT,
        ternary_encoded TEXT,
        status TEXT,
        retry_count INTEGER,
        created_at REAL
    )
    """)
    
    conn.commit()
    conn.close()
    print("[Ledger DB] Schema initialization complete.")

# Node helper functions
def register_node(node_id, address, public_key, status="Active", balance_usd=0.0, cpu_load=0.0, ram_usage=0.0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO nodes_registry (node_id, address, public_key, status, balance_usd, last_seen, cpu_load, ram_usage)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(node_id) DO UPDATE SET
        address=excluded.address,
        status=excluded.status,
        balance_usd=excluded.balance_usd,
        last_seen=excluded.last_seen,
        cpu_load=excluded.cpu_load,
        ram_usage=excluded.ram_usage
    """, (node_id, address, public_key, status, balance_usd, time.time(), cpu_load, ram_usage))
    conn.commit()
    conn.close()

def get_nodes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nodes_registry")
    rows = cursor.fetchall()
    nodes = [dict(row) for row in rows]
    conn.close()
    return nodes

# Task helper functions
def add_task(task_id, goal, executor_id="Local", status="Pending", output="", payout=0.0, signed_digest=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO task_ledger (task_id, goal, executor_id, status, output, payout, created_at, signed_digest)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(task_id) DO UPDATE SET
        executor_id=excluded.executor_id,
        status=excluded.status,
        output=excluded.output,
        signed_digest=excluded.signed_digest
    """, (task_id, goal, executor_id, status, output, payout, time.time(), signed_digest))
    conn.commit()
    conn.close()

def get_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM task_ledger ORDER BY created_at DESC")
    rows = cursor.fetchall()
    tasks = [dict(row) for row in rows]
    conn.close()
    return tasks

# Message queue helper functions
def enqueue_message(msg_id, sender, recipient, encrypted_payload, ternary_encoded):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO network_messages (msg_id, sender, recipient, encrypted_payload, ternary_encoded, status, retry_count, created_at)
    VALUES (?, ?, ?, ?, ?, 'Pending', 0, ?)
    """, (msg_id, sender, recipient, encrypted_payload, ternary_encoded, time.time()))
    conn.commit()
    conn.close()

def get_pending_messages():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM network_messages WHERE status='Pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    messages = [dict(row) for row in rows]
    conn.close()
    return messages

def mark_message_sent(msg_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE network_messages SET status='Sent' WHERE msg_id=?", (msg_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()
