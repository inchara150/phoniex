import docker
import os

def run_in_sandbox(project_path: str, test_command: str, image: str, install_command: str) -> dict:
    print(f"\n[🧪 SANDBOX] Initializing Docker client...")
    try:
        client = docker.from_env()
    except docker.errors.DockerException as e:
        return {"success": False, "logs": f"Failed to connect to Docker daemon: {e}"}

    abs_project_path = os.path.abspath(project_path)
    
    # Combine the install command and test command
    # e.g., "pip install -r requirements.txt && pytest tests/"
    full_command = f"sh -c '{install_command} && {test_command}'"
    
    print(f"[🧪 SANDBOX] Pulling lightweight image: {image} (if not cached)...")
    
    try:
        print(f"[🧪 SANDBOX] Mounting {abs_project_path}")
        print(f"[🧪 SANDBOX] Executing: {full_command}")
        
        container = client.containers.run(
            image=image,
            command=full_command,
            volumes={abs_project_path: {'bind': '/workspace', 'mode': 'rw'}},
            working_dir='/workspace',
            detach=True,
            remove=False
        )
        
        result = container.wait()
        exit_code = result.get('StatusCode', 1)
        logs = container.logs().decode('utf-8')
        container.remove(force=True)
        
        success = (exit_code == 0)
        
        if success:
            print("[🧪 SANDBOX] Execution completed successfully. Exit code: 0")
        else:
            print(f"[🧪 SANDBOX] Execution failed. Exit code: {exit_code}")
            
        return {
            "success": success,
            "logs": logs,
            "exit_code": exit_code
        }
        
    except Exception as e:
        print(f"[🧪 SANDBOX] Fatal sandbox error: {str(e)}")
        return {"success": False, "logs": str(e), "exit_code": -1}