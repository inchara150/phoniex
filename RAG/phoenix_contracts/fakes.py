"""Offline fakes for every interface (used in tests and demos)."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from .interfaces import Chunk


class FakeLLMClient:
    """Returns a canned reply or calls a user-supplied function; records prompts."""

    def __init__(self, reply: str | Callable[[str], str] = "FAKE_PATCH"):
        self._reply = reply
        self.prompts: List[str] = []

    def complete(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str:
        self.prompts.append(prompt)
        return self._reply(prompt) if callable(self._reply) else self._reply


class FakeRetriever:
    """Returns fixed chunks regardless of query (for testing consumers)."""

    def __init__(self, chunks: Optional[List[Chunk]] = None):
        self.chunks = chunks or []
        self.queries: List[str] = []

    def retrieve(self, query: str, k: int = 4, filters: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        self.queries.append(query)
        return list(self.chunks[:k])


class FakeSandboxRunner:
    def __init__(self, result: Optional[Dict[str, Any]] = None):
        self.result = result or {"returncode": 0, "stdout": "", "stderr": ""}
        self.calls: List[Sequence[str]] = []

    def run(self, project_dir: str, command: Sequence[str], timeout_s: int = 60) -> Dict[str, Any]:
        self.calls.append(command)
        return dict(self.result)


class FakeGitHubClient:
    def __init__(self):
        self.branches: List[str] = []
        self.commits: List[Dict[str, Any]] = []
        self.pull_requests: List[Dict[str, str]] = []

    def create_branch(self, repo: str, base: str, name: str) -> None:
        self.branches.append(name)

    def commit_files(self, repo: str, branch: str, files: Dict[str, str], message: str) -> str:
        self.commits.append({"branch": branch, "files": files, "message": message})
        return f"fakesha{len(self.commits)}"

    def open_pull_request(self, repo: str, head: str, base: str, title: str, body: str) -> str:
        self.pull_requests.append({"head": head, "base": base, "title": title, "body": body})
        return f"https://github.com/{repo}/pull/{len(self.pull_requests)}"
