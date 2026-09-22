"""Node contract: `def node(state) -> dict` returning ONLY the keys it updates.

`instrument` wraps any node with latency + state-diff telemetry without
changing its signature, so it drops into LangGraph unchanged.
"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, Dict, Optional

from .state import PhoenixState
from .telemetry import TelemetryEvent, TelemetryLogger

Node = Callable[[PhoenixState], Dict[str, Any]]


def _summarise(value: Any, limit: int = 120) -> Any:
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"...(+{len(value) - limit} chars)"
    if isinstance(value, (list, tuple)):
        return f"<{type(value).__name__} len={len(value)}>"
    if isinstance(value, dict):
        return f"<dict keys={len(value)}>"
    return value


def instrument(name: str, logger: Optional[TelemetryLogger] = None) -> Callable[[Node], Node]:
    def deco(fn: Node) -> Node:
        @functools.wraps(fn)
        def wrapper(state: PhoenixState) -> Dict[str, Any]:
            t0 = time.perf_counter()
            update = fn(state)
            if logger:
                logger.emit(
                    TelemetryEvent(
                        node=name,
                        route=str(state.get("route", "")),
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        state_diff={k: _summarise(v) for k, v in update.items()},
                    )
                )
            return update

        return wrapper

    return deco
