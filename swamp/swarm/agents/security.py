from phoenix_contracts.state import PhoenixState
from phoenix_contracts.interfaces import LLMClient

SYSTEM = """
You are a Security auditor. Identify injection, auth bypass, or secrets
exposure in the error context. Output a hardened patch and a one-line CVE tag.
No prose beyond the CVE tag.
"""

def security_agent(state: PhoenixState, llm: LLMClient) -> dict:
    user = f"ERROR:\n{state['error_trace']}\n\nFUNCTION:\n{state['target_function']}"
    patch = llm.complete(system=SYSTEM, user=user)
    return {"generated_patch": patch, "specialist_output": patch}
