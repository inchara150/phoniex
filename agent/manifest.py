import os
import yaml

def load_manifest(project_path: str) -> dict:
    """Reads and parses the .agent-manifest.yaml using your exact schema."""
    # Note: Ensure the filename matches exactly what is in your folder
    manifest_path = os.path.join(project_path, ".agent-manifest.yaml")
    
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
        
    with open(manifest_path, "r") as file:
        manifest = yaml.safe_load(file)
        
    try:
        # Extract the necessary values based on your nested schema
        return {
            "project_name": manifest["project"]["name"],
            "docker_image": manifest["sandbox"]["base_image"],
            "install_command": manifest["sandbox"]["install_command"],
            "test_command": manifest["verification"]["test_command"],
            "framework": manifest["project"]["framework"]
        }
    except KeyError as e:
        raise ValueError(f"Invalid manifest schema: missing required key {e}")