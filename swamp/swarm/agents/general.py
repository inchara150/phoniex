from phoenix_contracts.state import PhoenixState
from phoenix_contracts.interfaces import LLMClient

SYSTEM = """
You are a general-purpose code repair agent. Given an error trace and target
function, produce a minimal corrective patch. Output only the patched function.
"""

def general_agent(state: PhoenixState, llm: LLMClient) -> dict:
    user = f"ERROR:\n{state['error_trace']}\n\nFUNCTION:\n{state['target_function']}"
    patch = llm.complete(system=SYSTEM, user=user)
    return {"generated_patch": patch, "specialist_output": patch}
