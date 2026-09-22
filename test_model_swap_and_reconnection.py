"""
Test Suite: Reconnection Restoration & Mid-Workflow Failover Verification

Tests:
1. Online model readiness: Verifies gemini-3.6-flash is active when online.
2. Offline model swap: Verifies qwen2.5-coder:7b is active when offline.
3. Reconnection restoration: Verifies gemini-3.6-flash is IMMEDIATELY restored when net returns.
4. Mid-workflow emergency failover: Verifies dynamic mid-flight model swap from gemini to qwen2.5-coder
   if internet is disconnected while workflow is running.
"""

import os
import sys
import time
import threading

from connectivity_manager import connectivity_manager
from offline_queue import offline_queue, OfflineEventStatus
from receiver import get_live_agent_status, run_live_healing_thread, AGENT_LIVE_TRACKER

def test_online_readiness_and_restoration():
    print("\n" + "=" * 65)
    print("TEST 1: Online Readiness & Dynamic Reconnection Restoration")
    print("=" * 65)

    # 1. Set online
    connectivity_manager.set_simulated_offline(False)
    status = get_live_agent_status()
    print(f"  [ONLINE] Active Model: {status['active_model']} | Task: {status['current_task']}")
    assert status["active_model"] == "gemini-3.6-flash", f"Expected gemini-3.6-flash, got {status['active_model']}"

    # 2. Set offline
    connectivity_manager.set_simulated_offline(True)
    status_off = get_live_agent_status()
    print(f"  [OFFLINE] Active Model: {status_off['active_model']} | Task: {status_off['current_task']}")
    assert status_off["active_model"] == "qwen2.5-coder:7b", f"Expected qwen2.5-coder:7b, got {status_off['active_model']}"

    # 3. Set online again ("when net came")
    print("  [NET RECONNECTING] Turning internet back on...")
    connectivity_manager.set_simulated_offline(False)
    status_reconnect = get_live_agent_status()
    print(f"  [RESTORED] Active Model: {status_reconnect['active_model']} | Task: {status_reconnect['current_task']}")
    assert status_reconnect["active_model"] == "gemini-3.6-flash", f"Failed to restore gemini-3.6-flash! Got {status_reconnect['active_model']}"
    print("  [SUCCESS] Model successfully restored to gemini-3.6-flash upon reconnection!")

def test_mid_workflow_failover():
    print("\n" + "=" * 65)
    print("TEST 2: Mid-Workflow In-Flight Failover (Gemini -> Qwen)")
    print("=" * 65)

    # Reset environment
    connectivity_manager.set_simulated_offline(False)
    offline_queue.clear()
    
    # Break app.py
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    app_py = os.path.join(curr_dir, "app.py")
    with open(app_py, "w", encoding="utf-8") as f:
        f.write('''def calculate_total(price, tax_rate):
    return price + tax_rate

def divide(a, b):
    return a / b

def get_user_name(user):
    return user["username"]

def average(numbers):
    return sum(numbers) / (len(numbers) - 1)
''')

    # Start live healing workflow in background thread while ONLINE
    print("  [STEP 1] Launching workflow online with gemini-3.6-flash...")
    t = threading.Thread(target=run_live_healing_thread, args=(curr_dir,), daemon=True)
    t.start()

    # Wait for Step 1 or 2 to start running with Gemini
    time.sleep(0.4)
    live = get_live_agent_status()
    print(f"  [IN-FLIGHT RUNNING] Step: {live['current_step']} | Model: {live['active_model']}")
    assert live["initial_model"] == "gemini-3.6-flash"

    # Now drop the connection IN THE MIDDLE OF EXECUTION!
    print("  [DISCONNECT TRIGGERED] Dropping internet connection mid-flight...")
    connectivity_manager.set_simulated_offline(True)

    # Wait for the workflow to complete
    t.join(timeout=15.0)
    
    final_status = get_live_agent_status()
    print(f"  [WORKFLOW COMPLETED] Status: {final_status['status']} | Model: {final_status['active_model']}")
    print(f"  [FAILOVER SWAP] Swapped: {final_status['swapped']} | Details: {final_status['swap_details']}")
    
    assert final_status["swapped"] is True, "Expected swapped to be True"
    assert final_status["active_model"] == "qwen2.5-coder:7b", f"Expected qwen2.5-coder:7b after mid-flight failover, got {final_status['active_model']}"
    assert final_status["status"] == "completed", "Workflow did not complete successfully!"

    # Verify failover log message was recorded
    failover_logs = [log for log in final_status["logs"] if "MID-WORKFLOW FAILOVER" in log]
    print(f"  [LOG CONFIRMATION] Found {len(failover_logs)} failover log(s):")
    for fl in failover_logs:
        safe_fl = fl.encode("ascii", errors="replace").decode("ascii")
        print(f"    -> {safe_fl}")
    print("  [ALL LOGS]:")
    for l in final_status.get("logs", []):
        print("      ", l.encode("ascii", errors="replace").decode("ascii"))

    # Verify event was persisted to offline_queue as SYNC_PENDING
    pending_events = offline_queue.get_sync_pending()
    print(f"  [OFFLINE QUEUE] Pending sync events: {len(pending_events)}")
    assert len(pending_events) >= 1, "Expected patch to be queued as SYNC_PENDING"

    # Now simulate reconnection and auto-sync
    print("  [RECONNECT & SYNC] Restoring internet. Auto-syncing pending offline work...")
    connectivity_manager.set_simulated_offline(False)
    time.sleep(1.0)
    
    post_reconnect_status = get_live_agent_status()
    print(f"  [POST-RECONNECT STATUS] Active Model: {post_reconnect_status['active_model']}")
    assert post_reconnect_status["active_model"] == "gemini-3.6-flash", "Model did not restore to gemini-3.6-flash after reconnect!"
    
    synced_events = offline_queue.list_all_events()
    for se in synced_events:
        print(f"    -> Event {se['event_id']} Status: {se['status']} | PR: {se['github_pr_url']}")
        assert se["status"] == OfflineEventStatus.SYNCED

    print("\n" + "=" * 65)
    print("ALL TESTS PASSED: Mid-Workflow Model Swap & Reconnect Restoration Verified!")
    print("=" * 65)

if __name__ == "__main__":
    test_online_readiness_and_restoration()
    test_mid_workflow_failover()
