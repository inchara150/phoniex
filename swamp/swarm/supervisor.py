from phoenix_contracts.state import PhoenixState
from phoenix_contracts.interfaces import LLMClient

ROUTE_SYSTEM = """
You are a routing agent. Given an error trace, output exactly one word:
database | migration | security | general
No explanation.
"""

def supervisor_node(state: PhoenixState, llm: LLMClient) -> dict:
    route = llm.complete(
        system=ROUTE_SYSTEM,
        user=state["error_trace"]
    ).strip().lower()

    valid = {"database", "migration", "security", "general"}
    if route not in valid:
        route = "general"

    return {"route": route}
