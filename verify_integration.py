import sys, os
sys.path.insert(0, '.')

print("=" * 55)
print("PHOENIX INTEGRATION VERIFICATION")
print("=" * 55)

errors = []

# 1. energy_meter
try:
    from energy_meter import measure_energy
    with measure_energy() as em:
        x = sum(range(1000000))
    j = em["energy_j"]
    pct = em["cpu_percent"]
    dur = em["duration_s"]
    print(f"[PASS] energy_meter    : {j:.3f} J | {pct:.1f}% CPU | {dur:.3f}s")
except Exception as e:
    errors.append(f"energy_meter: {e}")
    print(f"[FAIL] energy_meter    : {e}")

# 2. weights_db
try:
    from weights_db import log_outcome, get_learned_accuracy
    log_outcome("null_pointer", "local_edge", "qwen2.5-coder:7b", 1, True)
    log_outcome("null_pointer", "local_edge", "qwen2.5-coder:7b", 2, True)
    acc = get_learned_accuracy("null_pointer", "local_edge")
    print(f"[PASS] weights_db      : learned_accuracy={acc:.2f}")
except Exception as e:
    errors.append(f"weights_db: {e}")
    print(f"[FAIL] weights_db      : {e}")

# 3. grid_api forecast
try:
    from grid_api import GridCarbonAPI
    api = GridCarbonAPI()
    forecast = api.get_forecast("US-CAL-BANC", hours=3)
    fi = forecast[0]["carbonIntensity"]
    print(f"[PASS] grid_api        : {len(forecast)} forecast windows | first={fi}")
except Exception as e:
    errors.append(f"grid_api: {e}")
    print(f"[FAIL] grid_api        : {e}")

# 4. scheduler + adaptive weights
try:
    from scheduler import PhoenixScheduler
    s = PhoenixScheduler()
    d = s.evaluate_task(severity="high", bug_type="null_pointer", local_grid=350, cloud_grid=200)
    route = d["route"]
    model = d["selected_model"]
    print(f"[PASS] scheduler       : route={route} | model={model}")
except Exception as e:
    errors.append(f"scheduler: {e}")
    print(f"[FAIL] scheduler       : {e}")

# 5. delay_node window finder
try:
    from agent.brain import find_lowest_carbon_window
    windows = [
        {"datetime": "2024-01-01T00:00:00Z", "carbonIntensity": 300},
        {"datetime": "2024-01-01T03:00:00Z", "carbonIntensity": 80},
    ]
    w = find_lowest_carbon_window(windows)
    print(f"[PASS] delay_window    : lowest={w['carbonIntensity']} at {w['datetime']}")
except Exception as e:
    errors.append(f"delay_window: {e}")
    print(f"[FAIL] delay_window    : {e}")

# 6. carbon budget guard - verify PhoenixState fields
try:
    from agent.brain import PhoenixState
    import typing
    hints = typing.get_type_hints(PhoenixState)
    assert "carbon_budget_g" in hints
    assert "carbon_spent_g" in hints
    print(f"[PASS] carbon_budget   : PhoenixState has carbon_budget_g + carbon_spent_g")
except Exception as e:
    errors.append(f"carbon_budget: {e}")
    print(f"[FAIL] carbon_budget   : {e}")

# 7. dashboard
try:
    import ast
    with open("dashboard.py", "r") as f:
        src = f.read()
    ast.parse(src)
    print(f"[PASS] dashboard.py    : valid Python syntax")
except Exception as e:
    errors.append(f"dashboard: {e}")
    print(f"[FAIL] dashboard.py    : {e}")

# 8. full offline pipeline
try:
    import subprocess
    r = subprocess.run(
        ["python", "-m", "pytest", "test_offline_pipeline.py", "-q"],
        capture_output=True, text=True, cwd="."
    )
    if "1 passed" in r.stdout:
        print(f"[PASS] offline_pipeline: 1/1 passed")
    else:
        raise Exception(r.stdout[-200:])
except Exception as e:
    errors.append(f"offline_pipeline: {e}")
    print(f"[FAIL] offline_pipeline: {e}")

# 9. RAG tests
try:
    r = subprocess.run(
        ["python", "-m", "pytest", "RAG/tests/test_rag.py", "-q"],
        capture_output=True, text=True, cwd="."
    )
    if "16 passed" in r.stdout or "17 passed" in r.stdout:
        count = "16" if "16 passed" in r.stdout else "17"
        print(f"[PASS] rag_tests       : {count}/16 passed")
    else:
        raise Exception(r.stdout[-200:])
except Exception as e:
    errors.append(f"rag_tests: {e}")
    print(f"[FAIL] rag_tests       : {e}")

print("=" * 55)
if errors:
    print(f"RESULT: {len(errors)} FAILURE(S)")
    for e in errors:
        print(f"  - {e}")
else:
    print(f"RESULT: ALL 9 CHECKS PASSED!")
print("=" * 55)
