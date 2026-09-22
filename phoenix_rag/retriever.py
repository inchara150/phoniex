from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from phoenix_contracts import Chunk, Embedder

from .chunking import chunk_paths
from .stores import InMemoryVectorStore


class VectorRetriever:
    """Satisfies the `Retriever` protocol."""

    def __init__(self, embedder: Embedder, store: Any = None):
        self.embedder = embedder
        self.store = store if store is not None else InMemoryVectorStore()

    def index_chunks(self, chunks: List[Chunk]) -> int:
        self.store.upsert(chunks, [self.embedder.embed(c.text) for c in chunks])
        return len(chunks)

    def index_directory(self, directory: str | Path, patterns: Iterable[str] = ("*.md",), **chunk_kw) -> int:
        paths = sorted(p for pat in patterns for p in Path(directory).rglob(pat))
        return self.index_chunks(chunk_paths(paths, **chunk_kw))

    def retrieve(self, query: str, k: int = 4, filters: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        return self.store.search(self.embedder.embed(query), k, filters)
