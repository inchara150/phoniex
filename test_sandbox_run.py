import os
from agent.manifest import load_manifest
from agent.sandbox import run_in_sandbox

# Point to your test app directory
target_path = os.path.abspath("test_app")

print(f"Testing manifest loading from: {target_path}")
manifest = load_manifest(target_path)
print("Parsed manifest successfully:")
for k, v in manifest.items():
    print(f"  {k}: {v}")

print("\nTriggering Docker execution sandbox...")
result = run_in_sandbox(
    project_path=target_path,
    test_command=manifest["test_command"],
    image=manifest["docker_image"],
    install_command=manifest["install_command"]
)

print(f"\nExecution Result: {'PASSED' if result['success'] else 'FAILED'}")
print(f"Exit Code: {result['exit_code']}")
print("Container Output:")
print(result["logs"])