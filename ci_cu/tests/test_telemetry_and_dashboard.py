import json, random
from phoenix_contracts import TelemetryEvent, append_event, read_events
from phoenix_dashboard import data
from phoenix_dashboard.simulator import simulate_run


def E(node, route="local", gco2=0.02, diff=None, **kw):
    return TelemetryEvent(node=node, route=route, gco2=gco2, state_diff=diff or {}, **kw)


def test_jsonl_roundtrip_and_shape(tmp_path):
    p = tmp_path / "t.jsonl"
    append_event(p, E("router", diff={"error_trace": "x"}, latency_ms=5, energy_j=1, cost_usd=0.1))
    d = json.loads(p.read_text().splitlines()[0])
    assert set(d) == {"timestamp", "node", "route", "latency_ms", "energy_j",
                      "gco2", "cost_usd", "state_diff"}
    evs, off = read_events(p)
    assert len(evs) == 1 and off == p.stat().st_size


def test_tail_ignores_partial_and_bad_lines(tmp_path):
    p = tmp_path / "t.jsonl"
    append_event(p, E("a"))
    with p.open("a") as f:
        f.write("not json\n")
        f.write('{"node":"half"')            # no newline yet
    evs, off = read_events(p)
    assert [e.node for e in evs] == ["a"]
    with p.open("a") as f:
        f.write(',"gco2":1}\n')              # writer finishes the line
    evs2, _ = read_events(p, off)
    assert [e.node for e in evs2] == ["half"]


def test_truncated_file_resets_offset(tmp_path):
    p = tmp_path / "t.jsonl"
    append_event(p, E("a")); append_event(p, E("b"))
    _, off = read_events(p)
    p.write_text(""); append_event(p, E("c"))
    evs, _ = read_events(p, off)
    assert [e.node for e in evs] == ["c"]


def test_fold_state_resets_on_new_run():
    evs = [E("router", diff={"error_trace": "one", "route": "local"}),
           E("database", diff={"generated_patch": "p1"}),
           E("router", route="cloud", diff={"error_trace": "two"})]
    s = data.fold_state(evs)
    assert s["error_trace"] == "two" and "generated_patch" not in s and s["route"] == "cloud"


def test_savings_only_for_local_model_calls():
    evs = [E("database", "local", 0.02), E("database", "cloud", 1.5),
           E("linter", "local", 0.001), E("sandbox", "local", 0.01)]
    s = data.summarize(evs, baseline_per_call=1.5)
    assert abs(s.saved_gco2 - 1.48) < 1e-9
    assert abs(s.baseline_gco2 - (s.total_gco2 + 1.48)) < 1e-9
    assert 0 < s.saved_pct < 100 and s.local_share == 0.5
    series = data.cumulative_series(evs, 1.5)
    assert series[-1]["cloud_only_gco2"] > series[-1]["actual_gco2"]


def test_local_call_costing_more_than_baseline_never_negative():
    assert data.saved_gco2(E("database", "local", 9.0), 1.5) == 0.0


def test_diff_html_and_unified():
    html, uni = data.diff_from_state({"target_function": "a=1\nb=2", "generated_patch": "a=1\nb=3"})
    assert uni is None and "<table" in html and "b=3" in html
    html, uni = data.diff_from_state({"generated_patch": "--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y"})
    assert html is None and uni.startswith("---")
    assert data.diff_from_state({}) == (None, None)


def test_simulator_events_are_contract_valid_and_dashboard_ready(tmp_path):
    rng = random.Random(1)
    evs = [e for _ in range(20) for e in simulate_run(rng)]
    for e in evs:
        TelemetryEvent.from_dict(json.loads(e.to_json()))
    s = data.summarize(evs)
    assert s.runs == 20 and s.saved_gco2 > 0
    assert data.fuzz_stats(evs)["runs"] >= 20 * 3
    assert data.per_node_table(evs)


def test_diff_html_escapes_model_output():
    html, _ = data.diff_from_state({"target_function": "x=1",
                                    "generated_patch": "x=1\n<script>alert(1)</script>"})
    assert "<script>alert" not in html and "&lt;script&gt;" in html
