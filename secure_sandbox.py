import os
import shutil
import tempfile
from contextlib import contextmanager

class PhoenixSecurityPolicies:
    MAX_RAM = "512m"
    MAX_CPUS = "1.0"
    NETWORK = "none"       # Total air-gap for test execution
    TIMEOUT_SECONDS = 30

@contextmanager
def ephemeral_workspace(source_project_path: str):
    """
    Creates an isolated clone of the project directory.
    Guarantees cleanup even if execution fails or crashes.
    """
    temp_dir = tempfile.mkdtemp(prefix="phoenix_sandbox_")
    try:
        if os.path.exists(source_project_path):
            for item in os.listdir(source_project_path):
                s = os.path.join(source_project_path, item)
                d = os.path.join(temp_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def generate_two_stage_execution(temp_workspace: str, image: str, install_cmd: str, test_cmd: str) -> tuple:
    """
    Generates:
    1. A build command (Network ON) to resolve dependencies.
    2. A run command (Network OFF, CPU/RAM quotas) to run untrusted tests.
    """
    policies = PhoenixSecurityPolicies
    custom_image_tag = f"phoenix_test_{os.path.basename(temp_workspace).lower()}"
    
    dockerfile_content = f"""FROM {image}
WORKDIR /workspace
COPY . /workspace
RUN {install_cmd}
"""
    
    dockerfile_path = os.path.join(temp_workspace, "Dockerfile")
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content.strip())
        
    build_command = f"docker build -t {custom_image_tag} {temp_workspace}"
    
    run_command = (
        f"docker run --rm "
        f"--network {policies.NETWORK} "
        f"--memory={policies.MAX_RAM} "
        f"--cpus={policies.MAX_CPUS} "
        f"{custom_image_tag} "
        f"sh -c '{test_cmd}'"
    )
    
    return build_command, run_command

if __name__ == "__main__":
    print("🛡️ Phoenix Secure Sandbox Module Loaded Successfully.")