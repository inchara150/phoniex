"""Sign a recorded payload and POST it to a running webhook (for the dry-run stage).

    python scripts/send_test_webhook.py phoenix_cicd/fixtures/workflow_run_failed.json \
        --event workflow_run --secret $PHOENIX_WEBHOOK_SECRET --url http://localhost:8080/webhook
"""
import argparse, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phoenix_cicd.security import sign  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("payload"); ap.add_argument("--event", required=True)
ap.add_argument("--secret", required=True); ap.add_argument("--url", default="http://localhost:8080/webhook")
a = ap.parse_args()
body = Path(a.payload).read_bytes()
req = urllib.request.Request(a.url, data=body, method="POST", headers={
    "Content-Type": "application/json", "X-GitHub-Event": a.event,
    "X-Hub-Signature-256": sign(a.secret, body)})
try:
    with urllib.request.urlopen(req) as r:
        print(r.status, r.read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())
