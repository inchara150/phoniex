import sqlite3
import os
import time
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline_resilience.db")

class OfflineEventStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED_OFFLINE = "COMPLETED_OFFLINE"
    SYNC_PENDING = "SYNC_PENDING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_offline_db():
    """Initializes the SQLite schema for offline event persistence."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_events (
                event_id TEXT PRIMARY KEY,
                timestamp REAL,
                created_at TEXT,
                project_path TEXT,
                error_type TEXT,
                error_message TEXT,
                stack_trace TEXT,
                target_function TEXT,
                status TEXT DEFAULT 'PENDING',
                generated_patch TEXT,
                test_logs TEXT,
                tests_passed BOOLEAN DEFAULT 0,
                local_model TEXT DEFAULT 'qwen2.5-coder:7b',
                carbon_gco2 REAL DEFAULT 0.90,
                sync_status TEXT DEFAULT 'PENDING',
                github_pr_url TEXT,
                synced_at TEXT,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON offline_events(status);
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sync_status ON offline_events(sync_status);
        ''')
        conn.commit()

class OfflineQueue:
    """
    SQLite-backed resilient queue for handling CI/CD failure events 
    when internet connectivity is lost.
    """
    def __init__(self):
        init_offline_db()

    def enqueue(
        self,
        project_path: str,
        error_type: str,
        error_message: str,
        stack_trace: str,
        target_function: Optional[str] = None,
        local_model: str = "qwen2.5-coder:7b"
    ) -> str:
        """Stores an incident locally when offline. Returns event_id."""
        init_offline_db()
        # Monotonic human-readable event id: evt_YYYYMMDD_HHMMSS_XXX
        t_now = time.time()
        dt_str = datetime.fromtimestamp(t_now).strftime("%Y%m%d_%H%M%S")
        suffix = int((t_now % 1) * 1000)
        event_id = f"evt_{dt_str}_{suffix:03d}"
        created_at = datetime.fromtimestamp(t_now).isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO offline_events (
                    event_id, timestamp, created_at, project_path, error_type,
                    error_message, stack_trace, target_function, status,
                    local_model, sync_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, t_now, created_at, project_path, error_type,
                error_message, stack_trace, target_function or "auto-detect",
                OfflineEventStatus.PENDING, local_model, "PENDING"
            ))
            conn.commit()
            
        print(f"[OFFLINE QUEUE] Enqueued event {event_id} ({error_type}) locally to SQLite.")
        return event_id

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single offline event by ID."""
        init_offline_db()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM offline_events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_pending_offline(self) -> List[Dict[str, Any]]:
        """Returns all events awaiting local offline execution."""
        init_offline_db()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM offline_events 
                WHERE status = ? 
                ORDER BY timestamp ASC
            ''', (OfflineEventStatus.PENDING,))
            return [dict(r) for r in cursor.fetchall()]

    def mark_processing(self, event_id: str):
        """Marks event as currently being repaired by local model."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE offline_events 
                SET status = ? 
                WHERE event_id = ?
            ''', (OfflineEventStatus.PROCESSING, event_id))
            conn.commit()

    def update_offline_result(
        self,
        event_id: str,
        generated_patch: str,
        test_logs: str,
        tests_passed: bool,
        carbon_gco2: float = 0.90
    ):
        """Saves generated local patch and sandbox outcome."""
        status = OfflineEventStatus.SYNC_PENDING if tests_passed else OfflineEventStatus.COMPLETED_OFFLINE
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE offline_events 
                SET status = ?,
                    generated_patch = ?,
                    test_logs = ?,
                    tests_passed = ?,
                    carbon_gco2 = ?,
                    sync_status = ?
                WHERE event_id = ?
            ''', (
                status, generated_patch, test_logs, 1 if tests_passed else 0,
                carbon_gco2, "PENDING" if tests_passed else "FAILED", event_id
            ))
            conn.commit()
        print(f"[OFFLINE QUEUE] Event {event_id} processed offline. Status: {status} (Tests Passed: {tests_passed}).")

    def mark_completed(
        self,
        event_id: str,
        generated_patch: str = "",
        tests_passed: bool = True,
        test_logs: str = "",
        carbon_gco2: float = 0.90
    ):
        """Convenience alias for update_offline_result."""
        return self.update_offline_result(event_id, generated_patch, test_logs, tests_passed, carbon_gco2)

    def get_sync_pending(self) -> List[Dict[str, Any]]:
        """Returns all completed offline events waiting for internet sync to push GitHub PRs."""
        init_offline_db()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM offline_events 
                WHERE status = ? OR (sync_status = 'PENDING' AND tests_passed = 1)
                ORDER BY timestamp ASC
            ''', (OfflineEventStatus.SYNC_PENDING,))
            return [dict(r) for r in cursor.fetchall()]

    def mark_synced(self, event_id: str, github_pr_url: str):
        """Marks an event as fully synchronized with GitHub once internet returns."""
        synced_at = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE offline_events 
                SET status = ?,
                    sync_status = 'SYNCED',
                    github_pr_url = ?,
                    synced_at = ?
                WHERE event_id = ?
            ''', (OfflineEventStatus.SYNCED, github_pr_url, synced_at, event_id))
            conn.commit()
        print(f"[OFFLINE RECONCILE] Event {event_id} synced! PR: {github_pr_url}")

    def mark_sync_failed(self, event_id: str, error_msg: str):
        """Marks an event as sync failed (increments retry count)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE offline_events 
                SET retry_count = retry_count + 1,
                    test_logs = test_logs || '\nSync Error: ' || ?
                WHERE event_id = ?
            ''', (error_msg, event_id))
            conn.commit()

    def list_all_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists events for dashboard display."""
        init_offline_db()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM offline_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_stats(self) -> Dict[str, int]:
        """Returns summary statistics of the offline queue."""
        init_offline_db()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'PROCESSING' THEN 1 ELSE 0 END) as processing,
                    SUM(CASE WHEN status = 'SYNC_PENDING' THEN 1 ELSE 0 END) as sync_pending,
                    SUM(CASE WHEN status = 'SYNCED' THEN 1 ELSE 0 END) as synced,
                    SUM(CASE WHEN tests_passed = 1 THEN 1 ELSE 0 END) as passed
                FROM offline_events
            ''')
            row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "pending": row["pending"] or 0,
                "processing": row["processing"] or 0,
                "sync_pending": row["sync_pending"] or 0,
                "synced": row["synced"] or 0,
                "passed": row["passed"] or 0
            }

    def clear(self):
        """Clears all records (useful for test resets)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM offline_events")
            conn.commit()

# Singleton instance
offline_queue = OfflineQueue()
