import os
import tempfile
import shutil

# Import our four standalone modules
from scheduler import PhoenixScheduler
from static_analysis import run_static_analysis
from ast_patcher import surgical_patch
from secure_sandbox import ephemeral_workspace, generate_two_stage_execution, PhoenixSecurityPolicies

def test_full_offline_pipeline():
    print("=" * 60)
    print("🚀 PHOENIX OFFLINE SUBSYSTEM INTEGRATION TEST")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Scheduler Decision Phase
    # ------------------------------------------------------------------
    print("\n[STEP 1] Evaluating Incident with Scheduler...")
    scheduler = PhoenixScheduler()
    incident_severity = "high"
    incident_complexity = "medium"

    routing_decision = scheduler.evaluate_task(
        severity=incident_severity,
        complexity=incident_complexity
    )
    route = routing_decision["route"]
    metrics = routing_decision["metrics"]

    print(f"  ↳ Route Selected : {route.upper()}")
    print(f"  ↳ Local Score    : {metrics['local_score']} | Cloud Score: {metrics['cloud_score']}")
    print(f"  ↳ Local Carbon   : {metrics['local_emissions_gCO2']}g | Cloud Carbon: {metrics['cloud_emissions_gCO2']}g")
    assert route in ["local_edge", "cloud_heavy", "delay"], "Invalid route assigned!"

    # ------------------------------------------------------------------
    # Step 2: Code Generation & Deterministic Linter Check
    # ------------------------------------------------------------------
    print("\n[STEP 2] Simulating LLM Output & Static Analysis...")

    # Sub-case A: Generator outputs a syntactically invalid patch
    bad_llm_patch = """
def load_data(conn)
    df = pd.read_csv('data.csv')
    return len(df)
"""
    lint_check_bad = run_static_analysis(bad_llm_patch, language="python")
    print(f"  ↳ Bad Patch Caught by Linter: {not lint_check_bad.is_valid}")
    assert not lint_check_bad.is_valid, "Linter failed to catch missing colon syntax error!"
    print(f"  ↳ Diagnostic Feedback Sent to Generator:\n    {lint_check_bad.issues[0]}")

    # Sub-case B: Generator iterates and produces a valid function
    valid_llm_patch = """
def load_data(conn):
    df = pd.read_csv('data.csv')
    df.rename(columns={'emp_id': 'id', 'full_name': 'name'}, inplace=True)
    df.to_sql('employees', conn, if_exists='append', index=False)
    return len(df)
"""
    lint_check_good = run_static_analysis(valid_llm_patch, language="python")
    print(f"  ↳ Good Patch Verified by Linter: {lint_check_good.is_valid}")
    assert lint_check_good.is_valid, "Linter rejected valid syntax!"

    # ------------------------------------------------------------------
    # Step 3: AST Surgical Patching
    # ------------------------------------------------------------------
    print("\n[STEP 3] Applying Surgical AST Patch to Source...")
    original_source = (
        "import pandas as pd\n"
        "from sqlalchemy import text\n\n"
        "# Preserved system comment\n"
        "class MetricsTracker:\n"
        "    pass\n\n"
        "def load_data(conn):\n"
        "    df = pd.read_csv('data.csv')\n"
        "    df.to_sql('employees', conn, if_exists='append', index=False)\n"
        "    return len(df)\n\n"
        "def secondary_helper():\n"
        "    return True\n"
    )

    patched_source = surgical_patch(
        original_code=original_source,
        llm_patch=valid_llm_patch,
        target_function="load_data"
    )

    assert "class MetricsTracker:" in patched_source, "AST patcher stripped existing classes!"
    assert "# Preserved system comment" in patched_source, "AST patcher stripped comments!"
    assert "df.rename(columns=" in patched_source, "AST patcher failed to apply the fix!"
    assert "def secondary_helper():" in patched_source, "AST patcher dropped adjacent functions!"
    print("  ↳ File successfully patched with 100% metadata/structure retention.")

    # ------------------------------------------------------------------
    # Step 4: Ephemeral Workspace Staging & Sandbox Command Generation
    # ------------------------------------------------------------------
    print("\n[STEP 4] Staging Ephemeral Workspace & Hardening Sandbox...")
    
    # Create a temporary local folder mimicking the project root
    mock_project_dir = tempfile.mkdtemp(prefix="phoenix_project_")
    with open(os.path.join(mock_project_dir, "ingest.py"), "w") as f:
        f.write(patched_source)
    with open(os.path.join(mock_project_dir, "test_ingest.py"), "w") as f:
        f.write("def test_dummy(): assert True")

    try:
        with ephemeral_workspace(mock_project_dir) as workspace_path:
            assert os.path.exists(os.path.join(workspace_path, "ingest.py")), "Failed to clone file to sandbox!"

            build_cmd, run_cmd = generate_two_stage_execution(
                temp_workspace=workspace_path,
                image="python:3.11-slim",
                install_cmd="pip install pandas sqlalchemy pytest",
                test_cmd="pytest test_ingest.py"
            )

            # Assert Dockerfile presence and security flags
            dockerfile_file = os.path.join(workspace_path, "Dockerfile")
            assert os.path.exists(dockerfile_file), "Sandbox failed to create Dockerfile!"
            assert f"--network {PhoenixSecurityPolicies.NETWORK}" in run_cmd, "Air-gap flag omitted!"
            assert f"--memory={PhoenixSecurityPolicies.MAX_RAM}" in run_cmd, "Memory ceiling omitted!"
            assert f"--cpus={PhoenixSecurityPolicies.MAX_CPUS}" in run_cmd, "CPU cap omitted!"

            print(f"  ↳ Ephemeral Workspace Verified : {workspace_path}")
            print(f"  ↳ Stage 1 Build Command        : {build_cmd}")
            print(f"  ↳ Stage 2 Air-Gapped Command   : {run_cmd}")

        assert not os.path.exists(workspace_path), "Ephemeral directory leaked after context exit!"
        print("  ↳ Ephemeral Workspace successfully scrubbed from disk.")

    finally:
        shutil.rmtree(mock_project_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print("✅ ALL OFFLINE SUBSYSTEMS PASSED INTEGRATION VALIDATION")
    print("=" * 60)

if __name__ == "__main__":
    test_full_offline_pipeline()