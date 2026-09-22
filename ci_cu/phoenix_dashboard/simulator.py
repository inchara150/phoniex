"""Emits realistic Phoenix telemetry so the dashboard can be built offline.

    python -m phoenix_dashboard.simulator --out telemetry.jsonl --runs 20 --interval 0.5
"""
from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

from phoenix_contracts import TelemetryEvent, append_event

GRID_G_PER_KWH = 650.0          # approx. carbon intensity of the local grid
J_PER_KWH = 3.6e6

SAMPLES = [
    ("sqlalchemy.exc.OperationalError: no such column: users.last_login",
     "database",
     "def get_user(db, uid):\n    return db.execute('SELECT id, name FROM users WHERE id=?', (uid,))\n",
     "def get_user(db, uid):\n    return db.execute('SELECT id, name, last_login FROM users WHERE id=?', (uid,))\n"),
    ("alembic.util.exc.CommandError: Target database is not up to date.",
     "alembic_migration",
     "def upgrade():\n    op.add_column('users', sa.Column('last_login', sa.DateTime))\n",
     "def upgrade():\n    op.add_column('users', sa.Column('last_login', sa.DateTime, nullable=True))\n    op.create_index('ix_users_last_login', 'users', ['last_login'])\n"),
    ("bandit B608: possible SQL injection via string-based query construction",
     "security_auditor",
     "def find(db, name):\n    return db.execute(f\"SELECT * FROM t WHERE name='{name}'\")\n",
     "def find(db, name):\n    return db.execute('SELECT * FROM t WHERE name=?', (name,))\n"),
]


def _gco2(energy_j: float) -> float:
    return energy_j / J_PER_KWH * GRID_G_PER_KWH


def simulate_run(rng: random.Random) -> list[TelemetryEvent]:
    trace, specialist, before, after = rng.choice(SAMPLES)
    route = "local" if rng.random() < 0.72 else "cloud"
    events: list[TelemetryEvent] = []

    def ev(node, *, r=None, lat, energy, cost=0.0, diff=None):
        gco2 = _gco2(energy)
        if node not in ("linter", "sandbox", "monte_carlo_fuzzer") and (r or route) == "cloud":
            gco2 = rng.uniform(0.9, 2.2)       # cloud inference incl. datacentre share
        events.append(TelemetryEvent(node=node, route=r or route, latency_ms=round(lat, 1),
                                     energy_j=round(energy, 2), gco2=round(gco2, 6),
                                     cost_usd=round(cost, 6), state_diff=diff or {}))

    ev("router", lat=rng.uniform(8, 25), energy=rng.uniform(1, 4),
       diff={"error_trace": trace, "route": route})
    ev("rag_retriever", lat=rng.uniform(15, 60), energy=rng.uniform(3, 12),
       diff={"retrieved_chunks": rng.randint(2, 5)})
    heavy = route == "cloud"
    ev(specialist, lat=rng.uniform(900, 2500) if heavy else rng.uniform(1500, 6000),
       energy=rng.uniform(80, 200) if not heavy else rng.uniform(2, 6),
       cost=rng.uniform(0.004, 0.02) if heavy else 0.0,
       diff={"target_function": before, "generated_patch": after,
             "gco2_estimate": round(rng.uniform(0.01, 0.06), 4), "specialist": specialist})
    ev("linter", r="local", lat=rng.uniform(40, 120), energy=rng.uniform(2, 6),
       diff={"lint_ok": True})
    ev("sandbox", r="local", lat=rng.uniform(300, 1200), energy=rng.uniform(10, 40),
       diff={"sandbox_ok": rng.random() > 0.1})
    # Monte Carlo fuzzer: a burst of small runs
    for i in range(rng.randint(3, 8)):
        ev("monte_carlo_fuzzer", r="local", lat=rng.uniform(20, 90), energy=rng.uniform(1, 5),
           diff={"fuzz_run": i, "fuzz_pass": rng.random() > 0.08})
    return events


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="telemetry.jsonl")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--interval", type=float, default=0.3, help="seconds between events")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--fresh", action="store_true", help="truncate the file first")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    if a.fresh:
        Path(a.out).unlink(missing_ok=True)
    for r in range(a.runs):
        for e in simulate_run(rng):
            append_event(a.out, e)
            time.sleep(a.interval)
        print(f"run {r + 1}/{a.runs} written to {a.out}")


if __name__ == "__main__":
    main()
