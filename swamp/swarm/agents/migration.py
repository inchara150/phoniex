from phoenix_contracts.state import PhoenixState
from phoenix_contracts.interfaces import LLMClient

SYSTEM = """
You are an Alembic migration specialist. Identify schema drift or broken
migration chains. Output the corrected migration op or revised target function.
No prose, only code.
"""

def migration_agent(state: PhoenixState, llm: LLMClient) -> dict:
    user = f"ERROR:\n{state['error_trace']}\n\nFUNCTION:\n{state['target_function']}"
    patch = llm.complete(system=SYSTEM, user=user)
    return {"generated_patch": patch, "specialist_output": patch}
