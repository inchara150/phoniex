import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from phoenix_cicd.app import create_app
from phoenix_cicd.events import parse_failure
from phoenix_cicd.pipeline import FixPipeline, extract_target_file
from phoenix_cicd.security import sign, verify_signature
from phoenix_contracts import FakeGitHubClient, GitHubClient, read_events

FIX = Path(__file__).resolve().parents[1] / "phoenix_cicd" / "fixtures"
SECRET = "s3cret"
SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
ORIGINAL = "def total(xs):\n    return sum(xs) / len(xs)\n"
PATCHED = "def total(xs):\n    return sum(xs) / len(xs) if xs else 0\n"
TRACE = ('Traceback (most recent call last):\n  File "/home/runner/work/shop/shop/tests/test_x.py", line 4, in test\n'
         '    total([])\n  File "/home/runner/work/shop/shop/src/calc.py", line 2, in total\n'
         'ZeroDivisionError: division by zero')


def load(name): return json.loads((FIX / name).read_text())


def fixer_ok(state):
    return {"target_function": ORIGINAL, "generated_patch": PATCHED,
            "route": "local", "gco2_estimate": 0.03}


def make(fixer=fixer_ok, tmp_path=None):
    client = FakeGitHubClient(
        logs={f"acme/shop@{SHA}": TRACE},
        files={("acme/shop", "src/calc.py"): "import x\n\n" + ORIGINAL + "\nprint('end')\n"})
    tel = tmp_path / "tel.jsonl" if tmp_path else None
    app = create_app(secret=SECRET, pipeline=FixPipeline(client, fixer, telemetry_path=tel))
    return TestClient(app), client, tel


def post(tc, event, payload, secret=SECRET, sig=None):
    body = json.dumps(payload).encode()
    return tc.post("/webhook", content=body, headers={
        "X-GitHub-Event": event, "Content-Type": "application/json",
        "X-Hub-Signature-256": sig if sig is not None else sign(secret, body)})


# ---------- security ----------
def test_signature_valid_and_invalid():
    body = b'{"a":1}'
    assert verify_signature("k", body, sign("k", body))
    assert not verify_signature("k", body, sign("other", body))
    assert not verify_signature("k", body + b" ", sign("k", body))
    assert not verify_signature("k", body, None)
    assert not verify_signature("k", body, "sha1=abc")
    assert not verify_signature("", body, sign("", body))


def test_bad_signature_is_401_and_does_nothing():
    tc, client, _ = make()
    assert post(tc, "workflow_run", load("workflow_run_failed.json"), sig="sha256=bad").status_code == 401
    assert post(tc, "workflow_run", load("workflow_run_failed.json"), secret="wrong").status_code == 401
    assert not client.prs


def test_empty_secret_refuses_to_start():
    with pytest.raises(ValueError):
        create_app(secret="", pipeline=FixPipeline(FakeGitHubClient()))


# ---------- parsing ----------
def test_parse_recorded_payloads():
    f = parse_failure("check_run", load("check_run_failed.json"))
    assert f and f.kind == "check_run" and f.run_id == 998877 and f.head_branch == "feature/login"
    f = parse_failure("workflow_run", load("workflow_run_failed.json"))
    assert f and f.repo == "acme/shop" and f.key == f"acme/shop@{SHA}"
    assert parse_failure("workflow_run", load("workflow_run_success.json")) is None
    assert parse_failure("workflow_run", load("workflow_run_bot_branch.json")) is None   # loop guard
    assert parse_failure("push", {"action": "completed"}) is None
    p = load("workflow_run_failed.json"); p["action"] = "requested"
    assert parse_failure("workflow_run", p) is None


def test_extract_target_file_prefers_source_over_tests():
    assert extract_target_file(TRACE) == "src/calc.py"
    assert extract_target_file("src/app.py:12: ZeroDivisionError") == "src/app.py"
    assert extract_target_file('File "/usr/lib/python3/site-packages/x.py", line 1') is None


# ---------- end to end ----------
def test_failed_run_opens_pr_with_patched_file(tmp_path):
    tc, client, tel = make(tmp_path=tmp_path)
    r = post(tc, "workflow_run", load("workflow_run_failed.json"))
    assert r.status_code == 202
    assert client.branches == [("acme/shop", f"phoenix/fix-{SHA[:7]}", SHA)]
    assert client.commits[0]["path"] == "src/calc.py"
    assert PATCHED in client.commits[0]["content"] and ORIGINAL not in client.commits[0]["content"]
    assert "print('end')" in client.commits[0]["content"]           # rest of file untouched
    pr = client.prs[0]
    assert pr["base"] == "feature/login" and pr["head"].startswith("phoenix/")
    assert "0.03" in pr["body"] and "review" in pr["body"].lower()
    evs, _ = read_events(tel)                                       # dashboard-visible
    assert evs[-1].node == "cicd_webhook" and evs[-1].state_diff["pr_url"].endswith("/pull/1")


def test_check_run_and_workflow_run_for_same_commit_dedupe():
    tc, client, _ = make()
    assert post(tc, "workflow_run", load("workflow_run_failed.json")).status_code == 202
    assert post(tc, "check_run", load("check_run_failed.json")).json()["status"] == "duplicate"
    assert len(client.prs) == 1


def test_ping_success_and_bot_branch_are_ignored():
    tc, client, _ = make()
    body = b"{}"
    assert tc.post("/webhook", content=body, headers={"X-GitHub-Event": "ping",
                   "X-Hub-Signature-256": sign(SECRET, body)}).json()["status"] == "pong"
    assert post(tc, "workflow_run", load("workflow_run_success.json")).json()["status"] == "ignored"
    assert post(tc, "workflow_run", load("workflow_run_bot_branch.json")).json()["status"] == "ignored"
    assert not client.prs


@pytest.mark.parametrize("fixer,why", [
    (lambda s: {}, "no patch"),
    (lambda s: {"target_function": ORIGINAL, "generated_patch": ORIGINAL}, "identical"),
    (lambda s: {"target_function": "def nope(): pass", "generated_patch": "def nope(): 1"}, "not found"),
    (lambda s: (_ for _ in ()).throw(RuntimeError("boom")), "fixer error"),
])
def test_no_pr_when_fix_is_unusable_and_retry_allowed(fixer, why):
    tc, client, _ = make(fixer)
    assert post(tc, "workflow_run", load("workflow_run_failed.json")).status_code == 202
    assert not client.prs and not client.branches
    # claim was released so a later delivery can try again
    assert post(tc, "workflow_run", load("workflow_run_failed.json")).status_code == 202


def test_explicit_target_file_from_fixer_wins():
    client = FakeGitHubClient(logs={f"acme/shop@{SHA}": "no traceback here"},
                              files={("acme/shop", "lib/other.py"): ORIGINAL})
    def fx(s): return {**fixer_ok(s), "target_file": "lib/other.py"}
    tc = TestClient(create_app(secret=SECRET, pipeline=FixPipeline(client, fx)))
    post(tc, "workflow_run", load("workflow_run_failed.json"))
    assert client.commits[0]["path"] == "lib/other.py"


def test_fake_satisfies_protocol():
    assert isinstance(FakeGitHubClient(), GitHubClient)


# ---------- dry-run safety on the real client ----------
def test_pygithub_client_dry_run_never_writes(monkeypatch):
    from unittest.mock import MagicMock
    import phoenix_cicd.github_client as gc
    fake_gh = MagicMock()
    monkeypatch.setattr(gc, "Github", lambda token: fake_gh)
    c = gc.PyGithubClient("tok", dry_run=True)
    c.create_branch("a/b", "phoenix/x", "sha")
    c.commit_file("a/b", "phoenix/x", "f.py", "x", "m")
    pr = c.open_pr("a/b", "phoenix/x", "main", "t", "b")
    assert pr.dry_run and pr.url.startswith("dry-run://")
    assert not fake_gh.mock_calls, "dry-run must not touch the GitHub API"
    c2 = gc.PyGithubClient("tok", dry_run=False)
    c2.create_branch("a/b", "phoenix/x", "sha")
    fake_gh.get_repo.return_value.create_git_ref.assert_called_once_with("refs/heads/phoenix/x", "sha")
