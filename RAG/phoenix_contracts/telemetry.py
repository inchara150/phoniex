"""One telemetry event shape, appended as JSON lines.

The dashboard only ever reads this file, so it never needs the live graph.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Union


@dataclass
class TelemetryEvent:
    node: str
    route: str = ""
    latency_ms: float = 0.0
    energy_j: float = 0.0
    gco2: float = 0.0
    cost_usd: float = 0.0
    state_diff: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, separators=(",", ":"))


class TelemetryLogger:
    """Thread-safe JSONL appender. Pass path=None for a no-op logger."""

    def __init__(self, path: Optional[Union[str, Path]] = None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: TelemetryEvent) -> None:
        if not self.path:
            return
        with self._lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(event.to_json() + "\n")


def read_events(path: Union[str, Path]) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
