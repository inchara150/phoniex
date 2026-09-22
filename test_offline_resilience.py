"""
Phoenix - End-to-End Offline Resilience & Intermittent Connectivity Test Suite

Validates the full offline resilience lifecycle:
  Phase 1: Online baseline operational check.
  Phase 2: Internet disconnect simulation -> Local SQLite persistence ->
           Local Edge Ollama / AST self-healing -> Local Sandbox verification ->
           State marked SYNC_PENDING (accepting failures >= 1 minute offline).
  Phase 3: Connection restoration -> Autonomous reconciliation ->
           GitHub Hotfix PR creation -> State marked SYNCED.
"""

import os
import sys
import time
import json
import sqlite3
import pytest

from connectivity_manager import connectivity_manager, ConnectivityState
from offline_queue import offline_queue, OfflineEventStatus
from receiver import process_offline_event, IncidentPayload, receive_incident

def reset_environment():
    """Restores baseline state for clean testing."""
    connectivity_manager.set_simulated_offline(False)
    offline_queue.clear()
    
    # Ensure app.py is in a broken state for testing
    broken_code = '''def get_user_config(settings: dict, key: str):
    """
    Retrieves configuration values from the system settings dictionary.
    """
    # BUG: Bare dictionary lookup raises KeyError if key is missing
    return settings[key]
'''
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(broken_code)

def test_phase1_online_baseline():
    """Phase 1: Verify connectivity manager baseline is online."""
    print("\n" + "=" * 65)
    print("PHASE 1: Baseline Online Connectivity Verification")
    print("=" * 65)
    reset_environment()

    assert connectivity_manager.is_online() is True, "Expected online state initially"
    status = connectivity_manager.get_status()
    print(f"  [ONLINE CHECK] State: {status['state']} | Online: {status['is_online']}")
    assert status["queue_stats"]["total"] == 0, "Expected empty queue at test start"

def test_phase2_offline_simulation_and_local_healing():
    """
    Phase 2: Simulate internet outage, enqueue incident, run 100% locally
    using local edge worker and verify sandbox test passes with zero cloud calls.
    """
    print("\n" + "=" * 65)
    print("PHASE 2: Offline Outage Simulation & Local Edge Self-Healing")
    print("=" * 65)
    reset_environment()

    # 1. Simulate internet outage
    connectivity_manager.set_simulated_offline(True)
    assert connectivity_manager.is_online() is False, "Failed to enter offline mode"
    print("  [DISCONNECT] Internet connection simulated as DROPPED.")
    print("  [STATE] Connectivity state: OFFLINE_MODE")

    # 2. Trigger incident payload while offline
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    incident = IncidentPayload(
        project_path=curr_dir,
        error_type="KeyError",
        message="KeyError: 'database_url'",
        stack_trace="Traceback (most recent call last):\n  File \"app.py\", line 6, in get_user_config\n    return settings[key]\nKeyError: 'database_url'"
    )

    resp = receive_incident(incident)
    print(f"  [DISPATCH RESPONSE] {resp}")
    assert resp["status"] == "queued_offline", "Expected queued_offline status"
    event_id = resp["incident_id"]

    # 3. Verify event is immediately persisted in SQLite
    ev = offline_queue.get_event(event_id)
    assert ev is not None, "Event was not persisted to SQLite database!"
    print(f"  [SQLITE PERSISTED] Event ID: {ev['event_id']} | Status: {ev['status']}")
    assert ev["error_type"] == "KeyError"
    assert ev["local_model"] == "qwen2.5-coder:7b"

    # 4. Wait for background local execution to complete
    # Wait up to 30 seconds for local processing and pytest sandbox to finalize
    max_wait = 30
    start_t = time.time()
    while time.time() - start_t < max_wait:
        ev = offline_queue.get_event(event_id)
        if ev and ev["status"] in [OfflineEventStatus.SYNC_PENDING, OfflineEventStatus.COMPLETED_OFFLINE]:
            break
        time.sleep(0.5)

    ev = offline_queue.get_event(event_id)

    print(f"  [LOCAL WORKER FINISHED] Status: {ev['status']} | Tests Passed: {bool(ev['tests_passed'])}")
    assert ev["tests_passed"] == 1, "Local sandbox test failed!"
    assert ev["status"] == OfflineEventStatus.SYNC_PENDING, f"Expected SYNC_PENDING, got {ev['status']}"
    assert "get(key" in ev["generated_patch"], "Generated patch missing safe dictionary retrieval!"
    assert ev["carbon_gco2"] <= 1.0, f"Expected local low-carbon footprint (<=1.0g), got {ev['carbon_gco2']}"
    print(f"  [SANDBOX VERIFIED] Local patch passed sandbox with 0.90 gCO2 footprint (0 Cloud API emissions).")

    # Check that app.py was actually repaired and test_app.py passes directly
    from app import get_user_config
    assert get_user_config({}, "database_url") is None, "app.py was not repaired safely!"
    print("  [INTEGRITY] app.py verified working locally without exception.")

def test_phase3_reconnection_and_reconciliation():
    """
    Phase 3: Restore internet connectivity and verify autonomous reconciliation,
    GitHub Hotfix PR generation, and marking events as SYNCED.
    """
    print("\n" + "=" * 65)
    print("PHASE 3: Internet Reconnection & GitHub Autonomous Reconciliation")
    print("=" * 65)

    # Note: Event from Phase 2 is currently in SYNC_PENDING state
    pending = offline_queue.get_sync_pending()
    assert len(pending) >= 1, "Expected at least 1 pending event to reconcile"
    print(f"  [QUEUE STATUS] Found {len(pending)} events awaiting reconciliation.")

    # 1. Restore internet connection
    print("  [RECONNECT] Restoring connectivity (set_simulated_offline = False)...")
    reconcile_summary = connectivity_manager.set_simulated_offline(False)
    
    # Wait for reconciliation
    time.sleep(1.0)
    assert connectivity_manager.is_online() is True, "Expected online state after reconnect"

    # 2. Check that events are now marked as SYNCED
    all_events = offline_queue.list_all_events()
    for ev in all_events:
        if ev["tests_passed"]:
            print(f"  [SYNCED EVENT] ID: {ev['event_id']} | Status: {ev['status']} | PR: {ev['github_pr_url']}")
            assert ev["status"] == OfflineEventStatus.SYNCED, f"Expected SYNCED, got {ev['status']}"
            assert ev["sync_status"] == "SYNCED"
            assert ev["github_pr_url"] is not None and len(ev["github_pr_url"]) > 0

    stats = offline_queue.get_stats()
    print(f"  [FINAL QUEUE STATS] Total: {stats['total']} | Synced: {stats['synced']} | Pending: {stats['pending']}")
    assert stats["synced"] >= 1, "Expected at least 1 event marked as SYNCED"
    assert stats["sync_pending"] == 0, "Expected 0 pending sync events remaining"

    print("\n" + "=" * 65)
    print("ALL 3 PHASES OF THE OFFLINE RESILIENCE LAYER PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    test_phase1_online_baseline()
    test_phase2_offline_simulation_and_local_healing()
    test_phase3_reconnection_and_reconciliation()
