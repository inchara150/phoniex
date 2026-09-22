from phoenix_contracts.state import PhoenixState
from phoenix_contracts.interfaces import LLMClient

SYSTEM = """
You are a Database specialist. Given an error trace and target function,
produce a minimal corrective patch. Output only the patched function, no prose.
"""

def database_agent(state: PhoenixState, llm: LLMClient) -> dict:
    user = f"ERROR:\n{state['error_trace']}\n\nFUNCTION:\n{state['target_function']}"
    patch = llm.complete(system=SYSTEM, user=user)
    return {"generated_patch": patch, "specialist_output": patch}
