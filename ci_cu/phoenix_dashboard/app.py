"""Phoenix live telemetry dashboard.

    streamlit run phoenix_dashboard/app.py -- --log telemetry.jsonl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from phoenix_contracts import read_events  # noqa: E402
from phoenix_dashboard import data  # noqa: E402


def show_html(html: str, height: int) -> None:
    """Diff HTML comes from difflib.HtmlDiff, which escapes <, > and & in the
    (LLM-generated) code, so it is safe to embed. Falls back for older Streamlit."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=height, scrolling=True)


def show_df(df: pd.DataFrame) -> None:
    try:
        st.dataframe(df, width="stretch")
    except TypeError:                       # older Streamlit
        st.dataframe(df, use_container_width=True)


def _cli_default_log() -> str:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="telemetry.jsonl")
    args, _ = ap.parse_known_args(sys.argv[1:])
    return args.log


st.set_page_config(page_title="Phoenix Telemetry", page_icon="🔥", layout="wide")
st.title("🔥 Phoenix live telemetry")

with st.sidebar:
    log_path = st.text_input("Telemetry JSONL", _cli_default_log())
    baseline = st.number_input("Cloud-only gCO2 per model call",
                               min_value=0.0, value=data.DEFAULT_CLOUD_GCO2_PER_CALL, step=0.1,
                               help="What one model call would emit if it always ran in the cloud.")
    refresh = st.slider("Refresh (seconds)", 1, 10, 2)
    max_rows = st.slider("Recent events shown", 10, 200, 50)
    if st.button("Reset view"):
        st.session_state.pop("events", None)
        st.session_state.pop("offset", None)

st.session_state.setdefault("events", [])
st.session_state.setdefault("offset", 0)


def render() -> None:
    new, st.session_state.offset = read_events(log_path, st.session_state.offset)
    st.session_state.events.extend(new)
    events = st.session_state.events
    if not events:
        st.info(f"Waiting for events in `{log_path}`. Start the simulator: "
                "`python -m phoenix_dashboard.simulator --out telemetry.jsonl`")
        return

    s = data.summarize(events, baseline)
    c = st.columns(6)
    c[0].metric("Runs", s.runs)
    c[1].metric("Events", s.events)
    c[2].metric("gCO2 emitted", f"{s.total_gco2:.3f}")
    c[3].metric("gCO2 saved vs cloud-only", f"{s.saved_gco2:.3f}", f"{s.saved_pct:.0f}%")
    c[4].metric("Local route share", f"{s.local_share:.0%}")
    c[5].metric("Cost (USD)", f"${s.total_cost_usd:.3f}")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Current graph state")
        state = data.fold_state(events)
        a, b, c2 = st.columns(3)
        a.metric("Last node", state.get("_last_node", "-"))
        b.metric("Route", state.get("route", "-"))
        c2.metric("gco2_estimate", state.get("gco2_estimate", "-"))
        shown = {k: v for k, v in state.items() if not k.startswith("_")}
        st.json(shown, expanded=False)
    with right:
        st.subheader("gCO2: actual vs cloud-only baseline")
        df = pd.DataFrame(data.cumulative_series(events, baseline)).set_index("n")
        st.line_chart(df[["actual_gco2", "cloud_only_gco2"]])

    st.subheader("Patch diff")
    html, unified = data.diff_from_state(data.fold_state(events))
    if html:
        show_html(html, 380)
    elif unified:
        st.code(unified, language="diff")
    else:
        st.caption("No generated_patch in the current state yet.")

    t1, t2, t3 = st.tabs(["Per node", "Monte Carlo fuzzer", "Recent events"])
    with t1:
        show_df(pd.DataFrame(data.per_node_table(events)))
    with t2:
        f = data.fuzz_stats(events)
        x = st.columns(3)
        x[0].metric("Fuzz runs", f["runs"])
        x[1].metric("Passed", f["passed"])
        x[2].metric("Pass rate", f"{f['pass_rate']:.0%}")
    with t3:
        rows = [{"time": e.timestamp, "node": e.node, "route": e.route,
                 "latency_ms": e.latency_ms, "energy_j": e.energy_j,
                 "gco2": e.gco2, "cost_usd": e.cost_usd} for e in events[-max_rows:]][::-1]
        show_df(pd.DataFrame(rows))


if hasattr(st, "fragment"):
    st.fragment(run_every=refresh)(render)()
else:  # very old Streamlit: manual refresh only
    render()
