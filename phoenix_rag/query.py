"""Turn PhoenixState into several targeted retrieval queries."""
from __future__ import annotations

import re
from typing import List

from phoenix_contracts import PhoenixState

_EXC = re.compile(r"^\s*([A-Za-z_][\w.]*(?:Error|Exception|Warning|Exit|Interrupt))\b\s*:?\s*(.*)$")
_FRAME = re.compile(r'File "([^"]+)", line \d+, in (\S+)')


def parse_trace(trace: str) -> dict:
    exc_type, exc_msg = "", ""
    for line in reversed(trace.strip().splitlines()):
        m = _EXC.match(line)
        if m:
            exc_type, exc_msg = m.group(1).split(".")[-1], m.group(2).strip()
            break
    frames = _FRAME.findall(trace)
    return {"exc_type": exc_type, "exc_msg": exc_msg, "frames": frames}


def build_queries(state: PhoenixState, max_queries: int = 3) -> List[str]:
    trace = state.get("error_trace", "") or ""
    info = parse_trace(trace)
    exc_type = state.get("error_type") or info["exc_type"]
    func = state.get("target_function") or (info["frames"][-1][1] if info["frames"] else "")

    queries: List[str] = []
    if exc_type:
        queries.append(f"{exc_type} {info['exc_msg']}".strip())          # what failed
    if exc_type and func:
        queries.append(f"how to fix {exc_type} in {func}")               # where + how
    if info["frames"]:
        queries.append(" ".join(f for _, f in info["frames"][-3:]))      # call path vocabulary
    if not queries and trace:
        queries.append(trace.strip().splitlines()[-1])
    seen, out = set(), []
    for q in queries:
        if q and q not in seen:
            seen.add(q); out.append(q)
    return out[:max_queries]
