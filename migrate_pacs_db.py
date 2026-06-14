#!/usr/bin/env python3
"""
migrate_pacs_db.py
Idempotent DB migration helper to ensure pacs_metadata has the required columns
(CompressedManifestPath, PartsCount, OriginalPixelSHA256).

Usage:
  python migrate_pacs_db.py
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_ledger.db")

def table_columns(table_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = [row[1] for row in cur.fetchall()]
    finally:
        conn.close()
    return cols


def add_column_if_missing(table, name, typ):
    cols = table_columns(table)
    if name in cols:
        print(f"Column '{name}' already exists in {table} — skipping")
        return False
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
        conn.commit()
        print(f"Added column '{name}' to {table}")
        return True
    except Exception as e:
        print(f"Failed to add column '{name}' to {table}: {e}")
        return False
    finally:
        conn.close()


def ensure_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Nothing to migrate.")
        return

    table = 'pacs_metadata'
    cols = table_columns(table)
    if not cols:
        print(f"Table '{table}' does not exist or is empty. Creating minimal schema.")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pacs_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                PatientID TEXT,
                PatientName TEXT,
                StudyInstanceUID TEXT,
                Modality TEXT,
                FilePath TEXT
            )
        ''')
        conn.commit()
        conn.close()

    # Idempotent additions
    add_column_if_missing(table, 'CompressedManifestPath', 'TEXT')
    add_column_if_missing(table, 'PartsCount', 'INTEGER DEFAULT 0')
    add_column_if_missing(table, 'OriginalPixelSHA256', 'TEXT')

if __name__ == '__main__':
    ensure_migration()
