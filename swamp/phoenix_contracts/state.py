from typing import TypedDict, Optional, List

class PhoenixState(TypedDict):
    error_trace: str
    target_function: str
    generated_patch: Optional[str]
    route: Optional[str]            # "database" | "migration" | "security" | "general"
    retrieved_chunks: List[str]
    specialist_output: Optional[str]
    validation_passed: bool
    gco2_estimate: float
