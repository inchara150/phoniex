import random
from trace_scanner import TraceScanner
from benchmark_suite import AdvancedPhoenixScheduler

def generate_mock_traceback() -> str:
    """Randomly generates realistic Python stack traces."""
    traces = [
        # 1. Database Deadlock (Complex, Cloud-Heavy)
        'Traceback (most recent call last):\n  File "worker.py", line 42, in process_job\n    db.commit()\nsqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked',
        
        # 2. Syntax Error (Trivial, Edge-Friendly)
        'Traceback (most recent call last):\n  File "api/routes.py", line 12, in <module>\n    def get_user(id)\nSyntaxError: expected \':\'',
        
        # 3. Algorithm Bound (Medium)
        'Traceback (most recent call last):\n  File "math_utils.py", line 88, in calculate_matrix\n    val = matrix[i][j+1]\nIndexError: list index out of range',
        
        # 4. Docstring/Linter (Low Priority, Delay Candidate)
        'Traceback (most recent call last):\n  File "ci_pipeline.py", line 15, in lint_check\n    raise ValueError("PEP8 violation: missing module docstring")\nValueError: PEP8 violation: missing module docstring'
    ]
    return random.choice(traces)

def get_severity_for_bug(bug_type: str) -> str:
    """Maps the extracted bug type to a severity tier for the scheduler."""
    mapping = {
        "db_deadlock": "critical",
        "syntax": "high",
        "algorithm": "medium",
        "formatting": "low"  # We will map PEP8 ValueErrors here for the simulation
    }
    # Fallback to medium if not explicitly mapped
    return mapping.get(bug_type, "medium")

def run_end_to_end_pipeline(num_tests: int = 100):
    print("=" * 65)
    print("🌪️ PHOENIX END-TO-END OBSERVABILITY & ROUTING SIMULATION")
    print("=" * 65)

    scanner = TraceScanner()
    scheduler = AdvancedPhoenixScheduler()
    
    results = {"local_edge": 0, "cloud_heavy": 0, "delay": 0}

    for i in range(1, num_tests + 1):
        # 1. System crashes and generates a raw log
        raw_trace = generate_mock_traceback()
        
        # 2. Scanner intercepts and parses the log
        scanned_data = scanner.scan_traceback(raw_trace)
        
        # Hack for the simulation: Override ValueError to formatting if it's a PEP8 error
        if "PEP8" in scanned_data["error_message"]:
            scanned_data["bug_type"] = "formatting"
            
        severity = get_severity_for_bug(scanned_data["bug_type"])
        
        # 3. Fetch live grid carbon intensities (simulated)
        sim_local_grid = random.uniform(50.0, 600.0)
        sim_cloud_grid = random.uniform(50.0, 600.0)

        # 4. Scheduler makes the multivariable routing decision
        route = scheduler.evaluate_task(
            severity=severity, 
            bug_type=scanned_data["bug_type"], 
            local_grid=sim_local_grid, 
            cloud_grid=sim_cloud_grid
        )
        
        results[route] += 1

        # Print the first 5 tests to see the data flow in action
        if i <= 5:
            print(f"\n[INCIDENT #{i}]")
            print(f"  ↳ Crashed Function : {scanned_data['target_function']}")
            print(f"  ↳ Parsed Bug Type  : {scanned_data['bug_type'].upper()} (Severity: {severity.upper()})")
            print(f"  ↳ Grid Conditions  : Local={sim_local_grid:.0f}g, Cloud={sim_cloud_grid:.0f}g")
            print(f"  ↳ Routing Decision : {route.upper()}")

    print("\n" + "=" * 65)
    print("📊 FINAL ROUTING DISTRIBUTION:")
    print(f"  ↳ Local Edge  : {results['local_edge']} tasks")
    print(f"  ↳ Cloud Heavy : {results['cloud_heavy']} tasks")
    print(f"  ↳ Delayed     : {results['delay']} tasks shifted off-peak")
    print("=" * 65)

if __name__ == "__main__":
    run_end_to_end_pipeline(num_tests=100)