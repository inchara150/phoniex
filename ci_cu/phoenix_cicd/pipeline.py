"""Failure -> Phoenix graph -> branch + commit + PR."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from phoenix_contracts import (FailureEvent, GitHubClient, TelemetryEvent, append_event)

log = logging.getLogger("phoenix.pipeline")

# The Phoenix brain, seen from here: state dict in, dict of updated keys out.
Fixer = Callable[[dict[str, Any]], dict[str, Any]]

_TB = re.compile(r'File "([^"]+)", line \d+')
_PYTEST = re.compile(r"^([\w./\\-]+\.py):\d+:", re.M)
_RUNNER_PREFIX = re.compile(r".*/work/[^/]+/[^/]+/(.*)")


def extract_target_file(error_trace: str) -> str | None:
    """Best-effort: last non-library file in a traceback / pytest output.
    Prefers source files over test files. Better: have the fixer set `target_file`."""
    cands = _TB.findall(error_trace) + _PYTEST.findall(error_trace)
    clean: list[str] = []
    for c in cands:
        if "site-packages" in c or "/lib/python" in c or c.startswith("<"):
            continue
        m = _RUNNER_PREFIX.match(c)
        clean.append(m.group(1) if m else c.lstrip("./"))
    if not clean:
        return None
    src = [c for c in clean if "test" not in Path(c).name.lower()]
    return (src or clean)[-1]


@dataclass
class FixResult:
    status: str                  # pr_opened | skipped | failed
    reason: str = ""
    branch: str | None = None
    pr_url: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "pr_opened"


def noop_fixer(state: dict[str, Any]) -> dict[str, Any]:
    """Default until the real graph is wired in: produces no patch, so no PR."""
    return {}


class FixPipeline:
    def __init__(self, client: GitHubClient, fixer: Fixer = noop_fixer,
                 telemetry_path: str | Path | None = None, dry_run_label: bool = False):
        self.client, self.fixer = client, fixer
        self.telemetry_path = telemetry_path
        self.dry_run_label = dry_run_label

    def handle(self, f: FailureEvent) -> FixResult:
        t0 = time.perf_counter()
        error_trace = self.client.get_failure_log(f)
        state: dict[str, Any] = {"error_trace": error_trace, "repo": f.repo,
                                 "head_sha": f.head_sha, "trigger": f.kind}
        try:
            out = self.fixer(dict(state)) or {}
        except Exception as e:                                   # graph blew up
            log.exception("fixer failed")
            return self._finish(f, state, {}, FixResult("failed", f"fixer error: {e}"), t0)
        merged = {**state, **out}

        result = self._apply(f, merged)
        return self._finish(f, state, merged, result, t0)

    # ------------------------------------------------------------------
    def _apply(self, f: FailureEvent, s: dict[str, Any]) -> FixResult:
        patch, original = s.get("generated_patch"), s.get("target_function")
        if not patch or not original:
            return FixResult("skipped", "graph produced no patch")
        if patch.strip() == original.strip():
            return FixResult("skipped", "patch identical to original")

        path = s.get("target_file") or extract_target_file(s["error_trace"])
        if not path:
            return FixResult("skipped", "could not determine target file")
        content = self.client.get_file(f.repo, path, f.head_sha)
        if content is None:
            return FixResult("skipped", f"file not found: {path}")
        if original not in content:
            return FixResult("skipped", f"target_function not found verbatim in {path}")

        new_content = content.replace(original, patch, 1)
        branch = f"phoenix/fix-{f.head_sha[:7]}"
        self.client.create_branch(f.repo, branch, f.head_sha)
        self.client.commit_file(f.repo, branch, path, new_content,
                                f"phoenix: auto-fix for failing CI ({f.head_sha[:7]})")
        pr = self.client.open_pr(f.repo, head=branch, base=f.head_branch,
                                 title=f"Phoenix auto-fix: {f.name or 'CI failure'} ({f.head_sha[:7]})",
                                 body=self._pr_body(f, s, path))
        return FixResult("pr_opened", branch=branch, pr_url=pr.url)

    @staticmethod
    def _pr_body(f: FailureEvent, s: dict[str, Any], path: str) -> str:
        return (
            f"Automated fix proposed by Phoenix for a failing check on `{f.head_sha[:7]}`.\n\n"
            f"- Failing run: {f.html_url or f.run_id}\n"
            f"- File changed: `{path}`\n"
            f"- Route: `{s.get('route', 'unknown')}`\n"
            f"- Estimated gCO2: `{s.get('gco2_estimate', 'n/a')}`\n\n"
            "**Please review before merging.** Phoenix does not merge anything itself.\n\n"
            f"<details><summary>Error trace (tail)</summary>\n\n```\n{s['error_trace'][-1500:]}\n```\n</details>"
        )

    def _finish(self, f, state, merged, result: FixResult, t0: float) -> FixResult:
        log.info("%s %s -> %s %s", f.repo, f.head_sha[:7], result.status, result.reason)
        if self.telemetry_path:
            diff = {"error_trace": state["error_trace"][-2000:],
                    "ci_status": result.status, "ci_reason": result.reason}
            for k in ("target_function", "generated_patch", "gco2_estimate"):
                if k in merged:
                    diff[k] = merged[k]
            if result.pr_url:
                diff["pr_url"] = result.pr_url
            append_event(self.telemetry_path, TelemetryEvent(
                node="cicd_webhook", route=str(merged.get("route", "local")),
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                gco2=float(merged.get("gco2_estimate", 0.0) or 0.0), state_diff=diff))
        return result
