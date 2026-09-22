"""Generator-prompt helper. In Phoenix, call this where the generator node
currently builds its prompt; if `context_block` is empty it is a no-op."""
from __future__ import annotations

from phoenix_contracts import PhoenixState

SYSTEM = (
    "You are Phoenix, a careful Python bug-fixing agent. Return only the corrected "
    "function. Follow every retrieved project guideline; if one conflicts with the "
    "obvious fix, follow the guideline."
)


def build_generation_prompt(state: PhoenixState) -> str:
    sections = [
        f"## Error trace\n{state.get('error_trace', '').strip()}",
        f"## Target function ({state.get('target_function', '?')})\n```python\n{state.get('source_code', '').strip()}\n```",
    ]
    ctx = state.get("context_block", "")
    if ctx:
        sections.append(ctx)
    if state.get("critic_feedback"):
        sections.append(f"## Critic feedback from previous attempt\n{state['critic_feedback']}")
    sections.append("## Task\nProduce the fixed function.")
    return "\n\n".join(sections)
