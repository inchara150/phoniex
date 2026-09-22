import os
import sys
import redis
from rq import SimpleWorker, Queue
from rq.timeouts import TimerDeathPenalty

from agent.brain import phoenix_brain

class WindowsSimpleWorker(SimpleWorker):
    death_penalty_class = TimerDeathPenalty

def process_incident(payload):
    print("\n[PHOENIX WORKER] Routing incident to Phoenix LangGraph Brain...")
    
    initial_state = {
        "project_path": payload.get("project_path"),
        "error_type": payload.get("error_type"),
        "error_message": payload.get("message"),
        "stack_trace": payload.get("stack_trace"),
        "generated_patch": None,
        "critic_feedback": None,
        "critic_approved": False,
        "tests_passed": False,
        "iteration_count": 0,
        "test_logs": None
    }
    
    final_state = phoenix_brain.invoke(initial_state)
    
    print("\n[PHOENIX WORKER] Workflow cycle completed.")
    print(f"Final Patch:\n{final_state.get('generated_patch')}")
    return True

# Ensure agent/worker.py points here for RQ deserialization
os.makedirs("agent", exist_ok=True)
with open("agent/__init__.py", "w") as f:
    pass
with open("agent/worker.py", "w") as f:
    f.write("from worker_test import process_incident\n")

if __name__ == '__main__':
    try:
        redis_conn = redis.Redis(
            host='127.0.0.1',
            port=6379,
            db=0,
            protocol=2,
            health_check_interval=10,
            socket_keepalive=True,
            socket_timeout=None
        )
        redis_conn.ping()
        print("Connected to Redis successfully.")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        sys.exit(1)

    incident_queue = Queue('phoenix_incidents', connection=redis_conn)
    worker = WindowsSimpleWorker([incident_queue], connection=redis_conn)

    print("Starting Phoenix Queue Worker (Windows SimpleWorker)...")
    print("Listening on phoenix_incidents...")

    while True:
        try:
            worker.work()
        except KeyboardInterrupt:
            print("\nShutting down Phoenix Worker...")
            break
        except Exception as e:
            print(f"[RECONNECT] Redis connection refreshed: {e}")