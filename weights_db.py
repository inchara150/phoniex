import sqlite3
import os
import datetime

DB_PATH = "weights.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS route_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_type TEXT,
                route TEXT,
                model TEXT,
                attempts INTEGER,
                success BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def log_outcome(bug_type: str, route: str, model: str, attempts: int, success: bool):
    """Logs the final outcome of an agent workflow to the database."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO route_outcomes (bug_type, route, model, attempts, success)
            VALUES (?, ?, ?, ?, ?)
        ''', (bug_type, route, model, attempts, success))
        conn.commit()
    print(f"\n[🧠 LEARNING] Logged outcome: {bug_type} via {route} ({model}) - Success: {success}, Attempts: {attempts}")

def get_learned_accuracy(bug_type: str, route: str) -> float:
    """
    Returns learned historical accuracy [0.0 - 1.0] if at least 2 historical runs exist.
    Otherwise returns None.
    """
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Look at the 10 most recent runs for this specific bug and route
        c.execute('''
            SELECT attempts, success FROM route_outcomes
            WHERE bug_type = ? AND route = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (bug_type, route))
        rows = c.fetchall()
        
    if len(rows) < 2:
        return None  # Not enough data to confidently learn yet
        
    # Calculate score logic: 
    # Attempt 1 success = 1.0
    # Attempt 2 success = 0.7
    # Attempt 3 success = 0.4
    # Fail / Escalation = 0.0
    total_score = 0.0
    for attempts, success in rows:
        if not success:
            total_score += 0.0
        elif attempts == 1:
            total_score += 1.0
        elif attempts == 2:
            total_score += 0.7
        else:
            total_score += 0.4
            
    return total_score / len(rows)
