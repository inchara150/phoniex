"""Shared state schema.

This mirrors the subset of `PhoenixState` (agent/brain.py) that standalone
features read or write. When integrating, diff this file against the real
schema and reconcile key names -- that is the *only* place drift can happen.
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class PhoenixState(TypedDict, total=False):
    # --- produced by TraceScanner / upstream nodes -------------------------
    error_trace: str
    crash_file: str
    target_function: str
    error_type: str
    source_code: str          # current source of the target function
    severity: float           # 0..1, feeds the utility weights

    # --- routing / scheduling ----------------------------------------------
    route: str                # "local_edge" | "cloud_heavy" | "delay"
    gco2_estimate: float

    # --- generation / critic loop ------------------------------------------
    generated_patch: str
    critic_feedback: str
    iteration: int

    # --- written by the Agentic RAG node -----------------------------------
    rag_status: str           # "ok" | "skipped:<reason>" | "no_relevant_docs"
    rag_queries: List[str]
    retrieved_context: List[Dict[str, Any]]
    context_block: str        # ready-to-inject prompt text ("" if none)


ROUTES = ("local_edge", "cloud_heavy", "delay")
