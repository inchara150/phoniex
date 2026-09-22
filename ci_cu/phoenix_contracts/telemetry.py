"""Telemetry contract: one JSON shape, appended to a JSONL file.

The dashboard only ever reads this file, never the live graph.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class TelemetryEvent:
    node: str
    route: str = "local"            # "local" | "cloud" | anything your router emits
    latency_ms: float = 0.0
    energy_j: float = 0.0
    gco2: float = 0.0
    cost_usd: float = 0.0
    state_diff: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, separators=(",", ":"))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TelemetryEvent":
        return cls(
            node=str(d["node"]),
            route=str(d.get("route", "local")),
            latency_ms=float(d.get("latency_ms", 0.0)),
            energy_j=float(d.get("energy_j", 0.0)),
            gco2=float(d.get("gco2", 0.0)),
            cost_usd=float(d.get("cost_usd", 0.0)),
            state_diff=dict(d.get("state_diff") or {}),
            timestamp=str(d.get("timestamp") or utc_now_iso()),
        )


def append_event(path: str | Path, event: TelemetryEvent) -> None:
    """Append one event as a single line. Thread-safe within a process."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = event.to_json() + "\n"
    with _LOCK, p.open("a", encoding="utf-8") as f:
        f.write(line)


def read_events(path: str | Path, offset: int = 0) -> tuple[list[TelemetryEvent], int]:
    """Read complete lines from byte `offset`. Returns (events, new_offset).

    A half-written trailing line is left for the next call, and malformed
    lines are skipped, so a dashboard tailing a live file never crashes.
    """
    p = Path(path)
    if not p.exists():
        return [], 0
    size = p.stat().st_size
    if size < offset:          # file was truncated / rotated
        offset = 0
    events: list[TelemetryEvent] = []
    with p.open("rb") as f:
        f.seek(offset)
        data = f.read()
    consumed = 0
    for raw in data.splitlines(keepends=True):
        if not raw.endswith(b"\n"):
            break                # incomplete line, wait for more
        consumed += len(raw)
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            events.append(TelemetryEvent.from_dict(json.loads(text)))
        except (ValueError, KeyError, TypeError):
            continue
    return events, offset + consumed
