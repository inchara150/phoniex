"""Narrow interfaces every standalone feature codes against.

Real implementations and fakes both satisfy these Protocols, so swapping
fakes for real clients at integration time is a one-line change.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, runtime_checkable


@dataclass
class Chunk:
    id: str
    text: str
    source: str                       # file path or doc name
    heading: str = ""                 # nearest markdown heading
    score: float = 0.0                # relevance, set at retrieval time
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> List[float]: ...


@runtime_checkable
class Retriever(Protocol):
    def retrieve(
        self, query: str, k: int = 4, filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]: ...


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str: ...


@runtime_checkable
class SandboxRunner(Protocol):
    def run(self, project_dir: str, command: Sequence[str], timeout_s: int = 60) -> Dict[str, Any]: ...


@runtime_checkable
class GitHubClient(Protocol):
    def create_branch(self, repo: str, base: str, name: str) -> None: ...
    def commit_files(self, repo: str, branch: str, files: Dict[str, str], message: str) -> str: ...
    def open_pull_request(self, repo: str, head: str, base: str, title: str, body: str) -> str: ...
