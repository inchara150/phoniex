class WorkspacePayload(BaseModel):
    name: str
    path: str
    branch: Optional[str] = "main"

@app.get("/api/v1/workspaces")
def get_workspaces():
    config = load_models_config()
    return {"status": "ok", "workspaces": config.get("workspaces", [])}

@app.post("/api/v1/workspaces")
def add_workspace(payload: WorkspacePayload):
    config = load_models_config()
    if "workspaces" not in config:
        config["workspaces"] = []
    
    # Check if exists
    for ws in config["workspaces"]:
        if ws.get("path") == payload.path:
            return {"status": "exists", "workspace": ws}
            
    new_ws = {
        "name": payload.name,
        "path": payload.path,
        "branch": payload.branch,
        "manifest_created": False
    }
    config["workspaces"].append(new_ws)
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        
    return {"status": "added", "workspace": new_ws}

class RoutingRulePayload(BaseModel):
    task_type: str
    local_model: str
    cloud_model: str

@app.get("/api/v1/routing-rules")
def get_routing_rules():
    config = load_models_config()
    return {"status": "ok", "rules": config.get("routing_rules", {
        "syntax": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
        "db_deadlock": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "claude-3-5-sonnet-20240620"},
        "algorithm": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
        "formatting": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
        "KeyError": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"}
    })}

@app.post("/api/v1/routing-rules")
def update_routing_rule(payload: RoutingRulePayload):
    config = load_models_config()
    if "routing_rules" not in config:
        config["routing_rules"] = {
            "syntax": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
            "db_deadlock": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "claude-3-5-sonnet-20240620"},
            "algorithm": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
            "formatting": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
            "KeyError": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"}
        }
    
    config["routing_rules"][payload.task_type] = {
        "local_edge": payload.local_model,
        "cloud_heavy": payload.cloud_model
    }
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        
    return {"status": "updated", "rules": config["routing_rules"]}
