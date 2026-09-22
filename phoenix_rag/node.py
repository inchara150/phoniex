"""The Agentic RAG node.

'Agentic' here means the node makes decisions instead of blindly retrieving:
  1. gate     - skip when there is nothing to search for or the route is 'delay'
  2. plan     - build several targeted queries from the trace
  3. fuse     - Reciprocal Rank Fusion across the queries' results
  4. judge    - drop chunks below an absolute and a relative (vs. best hit) floor; report 'no_relevant_docs'
  5. budget   - pack the best chunks into a character budget (token proxy)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from phoenix_contracts import Chunk, PhoenixState, Retriever, TelemetryLogger, instrument

from .query import build_queries


def _rrf(result_lists: List[List[Chunk]], k_const: int = 60) -> List[Chunk]:
    fused: Dict[str, float] = {}
    best: Dict[str, Chunk] = {}
    for results in result_lists:
        for rank, c in enumerate(results):
            fused[c.id] = fused.get(c.id, 0.0) + 1.0 / (k_const + rank + 1)
            if c.id not in best or c.score > best[c.id].score:
                best[c.id] = c                      # keep the highest raw similarity
    return [best[i] for i in sorted(fused, key=fused.get, reverse=True)]


def format_context(chunks: List[Chunk]) -> str:
    if not chunks:
        return ""
    parts = ["## Project guidelines (retrieved; treat as constraints)"]
    for i, c in enumerate(chunks, 1):
        loc = f"{c.source} > {c.heading}" if c.heading else c.source
        parts.append(f"[{i}] ({loc})\n{c.text}")
    return "\n\n".join(parts)


def make_rag_node(
    retriever: Retriever,
    *,
    k: int = 4,
    per_query_k: int = 6,
    min_score: float = 0.12,
    relative_floor: float = 0.5,
    max_context_chars: int = 3000,
    skip_routes: tuple = ("delay",),
    telemetry: Optional[TelemetryLogger] = None,
):
    @instrument("rag", telemetry)
    def rag_node(state: PhoenixState) -> Dict[str, Any]:
        if state.get("route") in skip_routes:
            return {"rag_status": f"skipped:route={state.get('route')}", "rag_queries": [],
                    "retrieved_context": [], "context_block": ""}
        queries = build_queries(state)
        if not queries:
            return {"rag_status": "skipped:no_query", "rag_queries": [],
                    "retrieved_context": [], "context_block": ""}

        fused = _rrf([retriever.retrieve(q, k=per_query_k) for q in queries])
        top = max((c.score for c in fused), default=0.0)
        # absolute floor AND relative floor (drop hits far weaker than the best one)
        relevant = [c for c in fused if c.score >= min_score and c.score >= relative_floor * top]
        if not relevant:
            return {"rag_status": "no_relevant_docs", "rag_queries": queries,
                    "retrieved_context": [], "context_block": ""}

        picked, used = [], 0
        for c in relevant:
            if len(picked) >= k:
                break
            if used + len(c.text) > max_context_chars and picked:
                continue
            picked.append(c); used += len(c.text)
        return {"rag_status": "ok", "rag_queries": queries,
                "retrieved_context": [c.to_dict() for c in picked],
                "context_block": format_context(picked)}

    return rag_node
