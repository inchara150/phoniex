"""Parse GitHub webhook payloads into FailureEvent (or None to ignore)."""
from __future__ import annotations

from typing import Any

from phoenix_contracts import FailureEvent

FAILED = {"failure", "timed_out"}
BOT_BRANCH_PREFIX = "phoenix/"     # never react to our own fix branches (loop guard)


def parse_failure(event_type: str, payload: dict[str, Any]) -> FailureEvent | None:
    if payload.get("action") != "completed":
        return None
    repo = (payload.get("repository") or {}).get("full_name")
    if not repo:
        return None

    if event_type == "check_run":
        cr = payload.get("check_run") or {}
        if cr.get("conclusion") not in FAILED:
            return None
        branch = (cr.get("check_suite") or {}).get("head_branch") or ""
        out = cr.get("output") or {}
        summary = "\n".join(x for x in (out.get("title"), out.get("summary"),
                                        out.get("text")) if x)
        obj, kind = cr, "check_run"
    elif event_type == "workflow_run":
        wr = payload.get("workflow_run") or {}
        if wr.get("conclusion") not in FAILED:
            return None
        branch = wr.get("head_branch") or ""
        summary = ""
        obj, kind = wr, "workflow_run"
    else:
        return None

    sha, run_id = obj.get("head_sha"), obj.get("id")
    if not sha or run_id is None or not branch:
        return None
    if branch.startswith(BOT_BRANCH_PREFIX):
        return None
    return FailureEvent(repo=repo, head_sha=sha, head_branch=branch, kind=kind,
                        run_id=int(run_id), name=obj.get("name") or "",
                        html_url=obj.get("html_url") or "", summary=summary)
