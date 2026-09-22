"""Real GitHubClient built on PyGithub. Defaults to DRY-RUN: reads work, writes are only logged."""
from __future__ import annotations

import logging

import requests
from github import Github, GithubException

from phoenix_contracts import FailureEvent, PullRequestRef

log = logging.getLogger("phoenix.github")


class PyGithubClient:
    def __init__(self, token: str, dry_run: bool = True, max_log_chars: int = 20000):
        self._gh = Github(token)
        self._token = token
        self.dry_run = dry_run
        self.max_log_chars = max_log_chars

    # ------------------------- reads (always real) -------------------------
    def get_failure_log(self, failure: FailureEvent) -> str:
        text = self._job_logs(failure.repo, failure.run_id) if failure.kind == "check_run" \
            else self._workflow_logs(failure)
        text = text or failure.summary
        return text[-self.max_log_chars:]      # the tail holds the actual error

    def _job_logs(self, repo: str, job_id: int) -> str:
        # For GitHub Actions, check_run.id == job id.
        r = requests.get(f"https://api.github.com/repos/{repo}/actions/jobs/{job_id}/logs",
                         headers={"Authorization": f"Bearer {self._token}",
                                  "Accept": "application/vnd.github+json"}, timeout=30)
        return r.text if r.ok else ""

    def _workflow_logs(self, failure: FailureEvent) -> str:
        run = self._gh.get_repo(failure.repo).get_workflow_run(failure.run_id)
        parts = [self._job_logs(failure.repo, j.id)
                 for j in run.jobs() if j.conclusion in ("failure", "timed_out")]
        return "\n".join(p for p in parts if p)

    def get_file(self, repo: str, path: str, ref: str) -> str | None:
        try:
            item = self._gh.get_repo(repo).get_contents(path, ref=ref)
        except GithubException as e:
            if e.status == 404:
                return None
            raise
        if isinstance(item, list):
            return None
        return item.decoded_content.decode("utf-8")

    # ------------------------- writes (gated) -------------------------
    def create_branch(self, repo: str, name: str, from_sha: str) -> None:
        if self.dry_run:
            log.info("[dry-run] create branch %s on %s from %s", name, repo, from_sha)
            return
        self._gh.get_repo(repo).create_git_ref(f"refs/heads/{name}", from_sha)

    def commit_file(self, repo: str, branch: str, path: str, content: str, message: str) -> None:
        if self.dry_run:
            log.info("[dry-run] commit %s to %s@%s: %s", path, repo, branch, message)
            return
        r = self._gh.get_repo(repo)
        existing = r.get_contents(path, ref=branch)
        r.update_file(path, message, content, existing.sha, branch=branch)

    def open_pr(self, repo: str, head: str, base: str, title: str, body: str) -> PullRequestRef:
        if self.dry_run:
            log.info("[dry-run] open PR %s -> %s on %s: %s", head, base, repo, title)
            return PullRequestRef(number=0, url=f"dry-run://{repo}/{head}", dry_run=True)
        pr = self._gh.get_repo(repo).create_pull(title=title, body=body, head=head, base=base)
        return PullRequestRef(number=pr.number, url=pr.html_url)
