"""GitHub adapter contract + an in-memory fake for offline tests."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class FailureEvent:
    """A normalised 'CI failed' signal parsed from a GitHub webhook."""
    repo: str                # "owner/name"
    head_sha: str
    head_branch: str
    kind: str                # "check_run" | "workflow_run"
    run_id: int
    name: str = ""
    html_url: str = ""
    summary: str = ""        # any inline output GitHub gave us

    @property
    def key(self) -> str:
        """Idempotency key: one fix attempt per commit."""
        return f"{self.repo}@{self.head_sha}"


@dataclass(frozen=True)
class PullRequestRef:
    number: int
    url: str
    dry_run: bool = False


@runtime_checkable
class GitHubClient(Protocol):
    def get_failure_log(self, failure: FailureEvent) -> str: ...
    def get_file(self, repo: str, path: str, ref: str) -> str | None: ...
    def create_branch(self, repo: str, name: str, from_sha: str) -> None: ...
    def commit_file(self, repo: str, branch: str, path: str,
                    content: str, message: str) -> None: ...
    def open_pr(self, repo: str, head: str, base: str,
                title: str, body: str) -> PullRequestRef: ...


@dataclass
class FakeGitHubClient:
    """Records every write so tests can assert on it."""
    logs: dict[str, str] = field(default_factory=dict)              # failure.key -> log
    files: dict[tuple[str, str], str] = field(default_factory=dict)  # (repo, path) -> text
    branches: list[tuple[str, str, str]] = field(default_factory=list)
    commits: list[dict[str, Any]] = field(default_factory=list)
    prs: list[dict[str, Any]] = field(default_factory=list)

    def get_failure_log(self, failure: FailureEvent) -> str:
        return self.logs.get(failure.key, failure.summary)

    def get_file(self, repo: str, path: str, ref: str) -> str | None:
        return self.files.get((repo, path))

    def create_branch(self, repo: str, name: str, from_sha: str) -> None:
        self.branches.append((repo, name, from_sha))

    def commit_file(self, repo, branch, path, content, message) -> None:
        self.commits.append(dict(repo=repo, branch=branch, path=path,
                                 content=content, message=message))
        self.files[(repo, path)] = content

    def open_pr(self, repo, head, base, title, body) -> PullRequestRef:
        self.prs.append(dict(repo=repo, head=head, base=base, title=title, body=body))
        n = len(self.prs)
        return PullRequestRef(number=n, url=f"https://github.test/{repo}/pull/{n}")
