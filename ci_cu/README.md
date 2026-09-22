# Phoenix: telemetry dashboard + CI/CD webhook

Both modules talk to Phoenix only through `phoenix_contracts/`.

```
phoenix_contracts/   telemetry.py (event + JSONL append/tail)   github.py (FailureEvent, GitHubClient, FakeGitHubClient)
phoenix_dashboard/   data.py (pure logic)  simulator.py  app.py (Streamlit)
phoenix_cicd/        security.py (HMAC)  events.py (payload parsing)  pipeline.py (failure -> PR)
                     app.py (FastAPI)  github_client.py (PyGithub, dry-run default)  main.py (env wiring)
                     fixtures/ (recorded payloads)
scripts/send_test_webhook.py    tests/ (24 tests, all offline)
```

## Run

```bash
pip install -r requirements.txt && pytest -q

# Dashboard, developed against the simulator
python -m phoenix_dashboard.simulator --out telemetry.jsonl --runs 20 --interval 0.5 --fresh &
streamlit run phoenix_dashboard/app.py -- --log telemetry.jsonl

# Webhook, dry-run (default): reads from GitHub, writes are only logged
export PHOENIX_WEBHOOK_SECRET=... GITHUB_TOKEN=... PHOENIX_DRY_RUN=1
uvicorn phoenix_cicd.main:app_factory --factory --port 8080
python scripts/send_test_webhook.py phoenix_cicd/fixtures/workflow_run_failed.json \
       --event workflow_run --secret $PHOENIX_WEBHOOK_SECRET
```

## Integration (the three wiring steps)

1. **Fixer**: `export PHOENIX_FIXER=brain:run_fix`, where `run_fix(state: dict) -> dict` invokes your compiled graph
   and returns `generated_patch`, `target_function` (+ optionally `target_file`, `route`, `gco2_estimate`).
2. **Telemetry**: point `PHOENIX_TELEMETRY_PATH` and the dashboard `--log` at the same file your graph nodes append to.
3. **Real clients**: `PyGithubClient` is already the real one; go live with `PHOENIX_DRY_RUN=0` only after a dry-run passes.

## Conventions I assumed (check against your PhoenixState)

- `target_function` = original source text, `generated_patch` = replacement text. The PR swaps one for the other
  inside the file (verbatim match required, otherwise no PR). A unified-diff patch is displayed correctly in the dashboard
  but is not applied by the webhook.
- A telemetry event whose `state_diff` contains `error_trace` starts a new run in the dashboard.
- gCO2 saved = (cloud-only gCO2 per call, default 1.5, adjustable in the sidebar) minus actual, for local-route model calls.
- If you already have `phoenix_contracts` from Step 0, keep yours and only check that these names/fields match.

## Safety built in

HMAC on the raw body (constant-time), 401 on mismatch; refuses to start with an empty secret; ignores branches
starting with `phoenix/` (no fix-on-fix loops); one attempt per (repo, sha) even when both `check_run` and
`workflow_run` fire; PR only, never merges; work runs in a background task so GitHub's 10s timeout isn't hit.
