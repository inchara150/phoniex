"""Pure functions that turn telemetry events into what the dashboard shows.

No Streamlit imports here, so everything is unit-testable.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any, Iterable

from phoenix_contracts import TelemetryEvent

# Nodes that are not model calls: their emissions are identical with or
# without a cloud-only baseline, so they never count towards "saved".
NON_MODEL_NODES = {"linter", "sandbox", "monte_carlo_fuzzer", "cicd_webhook",
                   "rag_retriever"}

DEFAULT_CLOUD_GCO2_PER_CALL = 1.5   # assumption: tune to your own measurement


def is_model_call(e: TelemetryEvent) -> bool:
    return e.node not in NON_MODEL_NODES


def saved_gco2(e: TelemetryEvent, baseline_per_call: float) -> float:
    """gCO2 avoided vs running this call on the cloud."""
    if is_model_call(e) and e.route == "local":
        return max(baseline_per_call - e.gco2, 0.0)
    return 0.0


def fold_state(events: Iterable[TelemetryEvent]) -> dict[str, Any]:
    """Rebuild the 'current' PhoenixState by applying state_diffs in order.

    A diff containing `error_trace` marks the start of a new run and resets state.
    """
    state: dict[str, Any] = {}
    for e in events:
        if "error_trace" in e.state_diff:
            state = {}
        state.update(e.state_diff)
        state["route"] = e.route if "route" not in e.state_diff else state["route"]
        state["_last_node"] = e.node
        state["_last_timestamp"] = e.timestamp
    return state


@dataclass
class Summary:
    events: int = 0
    runs: int = 0
    total_gco2: float = 0.0
    baseline_gco2: float = 0.0
    saved_gco2: float = 0.0
    total_cost_usd: float = 0.0
    total_energy_j: float = 0.0
    avg_latency_ms: float = 0.0
    local_share: float = 0.0

    @property
    def saved_pct(self) -> float:
        return 100.0 * self.saved_gco2 / self.baseline_gco2 if self.baseline_gco2 else 0.0


def summarize(events: list[TelemetryEvent],
              baseline_per_call: float = DEFAULT_CLOUD_GCO2_PER_CALL) -> Summary:
    if not events:
        return Summary()
    total = sum(e.gco2 for e in events)
    saved = sum(saved_gco2(e, baseline_per_call) for e in events)
    calls = [e for e in events if is_model_call(e)]
    local = [e for e in calls if e.route == "local"]
    return Summary(
        events=len(events),
        runs=sum(1 for e in events if "error_trace" in e.state_diff),
        total_gco2=total,
        baseline_gco2=total + saved,
        saved_gco2=saved,
        total_cost_usd=sum(e.cost_usd for e in events),
        total_energy_j=sum(e.energy_j for e in events),
        avg_latency_ms=sum(e.latency_ms for e in events) / len(events),
        local_share=len(local) / len(calls) if calls else 0.0,
    )


def cumulative_series(events: list[TelemetryEvent],
                      baseline_per_call: float = DEFAULT_CLOUD_GCO2_PER_CALL
                      ) -> list[dict[str, Any]]:
    """Per-event cumulative actual vs cloud-only baseline gCO2."""
    rows, actual, base = [], 0.0, 0.0
    for i, e in enumerate(events, 1):
        actual += e.gco2
        base += e.gco2 + saved_gco2(e, baseline_per_call)
        rows.append({"n": i, "timestamp": e.timestamp,
                     "actual_gco2": actual, "cloud_only_gco2": base})
    return rows


def per_node_table(events: list[TelemetryEvent]) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, float]] = {}
    for e in events:
        a = agg.setdefault(e.node, dict(calls=0, latency_ms=0.0, energy_j=0.0,
                                        gco2=0.0, cost_usd=0.0))
        a["calls"] += 1
        a["latency_ms"] += e.latency_ms
        a["energy_j"] += e.energy_j
        a["gco2"] += e.gco2
        a["cost_usd"] += e.cost_usd
    return [{"node": n, "calls": int(a["calls"]),
             "avg_latency_ms": round(a["latency_ms"] / a["calls"], 1),
             "energy_j": round(a["energy_j"], 2),
             "gco2": round(a["gco2"], 5),
             "cost_usd": round(a["cost_usd"], 5)}
            for n, a in sorted(agg.items())]


def fuzz_stats(events: list[TelemetryEvent]) -> dict[str, Any]:
    """Monte Carlo fuzzer panel. Reads fuzz_pass from each fuzzer event's diff."""
    runs = [e for e in events if e.node == "monte_carlo_fuzzer"]
    passed = sum(1 for e in runs if e.state_diff.get("fuzz_pass") is True)
    return {"runs": len(runs), "passed": passed, "failed": len(runs) - passed,
            "pass_rate": passed / len(runs) if runs else 0.0}


# ----------------------------- diff -----------------------------

def looks_like_unified_diff(text: str) -> bool:
    head = text.lstrip().splitlines()[:3]
    return any(l.startswith(("--- ", "+++ ", "@@ ")) for l in head)


def build_diff_html(original: str, patched: str, context: int = 3) -> str:
    """Side-by-side HTML diff via difflib (original left, patched right)."""
    return difflib.HtmlDiff(tabsize=4, wrapcolumn=72).make_file(
        original.splitlines(), patched.splitlines(),
        fromdesc="original (target_function)", todesc="patched (generated_patch)",
        context=True, numlines=context)


def diff_from_state(state: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (html_side_by_side, raw_unified_diff). At most one is non-None.

    Convention: `target_function` holds the original source and
    `generated_patch` the replacement. If the patch is already a unified diff
    it is shown as-is.
    """
    patch = state.get("generated_patch")
    if not patch:
        return None, None
    if looks_like_unified_diff(patch):
        return None, patch
    original = state.get("target_function") or ""
    return build_diff_html(original, patch), None
