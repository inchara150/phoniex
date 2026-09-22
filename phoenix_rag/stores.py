"""Vector stores. `InMemoryVectorStore` needs no dependencies; `QdrantStore`
wraps qdrant-client (local :memory:, on-disk path, or server URL)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from phoenix_contracts import Chunk


def _matches(chunk: Chunk, filters: Optional[Dict[str, Any]]) -> bool:
    return all(chunk.metadata.get(k) == v for k, v in (filters or {}).items())


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._items: Dict[str, Tuple[Chunk, List[float]]] = {}

    def __len__(self) -> int:
        return len(self._items)

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        for c, v in zip(chunks, vectors):
            self._items[c.id] = (c, list(v))

    def search(self, vector: Sequence[float], k: int, filters: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        scored = []
        for chunk, vec in self._items.values():
            if _matches(chunk, filters):
                scored.append((sum(a * b for a, b in zip(vector, vec)), chunk))
        scored.sort(key=lambda t: t[0], reverse=True)
        out = []
        for s, c in scored[:k]:
            out.append(Chunk(**{**c.to_dict(), "score": float(s)}))
        return out


class QdrantStore:
    """Requires `pip install qdrant-client`. Untested offline -- see README."""

    def __init__(self, dim: int, collection: str = "phoenix_docs",
                 location: str = ":memory:", url: Optional[str] = None, path: Optional[str] = None):
        from qdrant_client import QdrantClient, models  # lazy: optional dependency

        self._models = models
        self.collection = collection
        if url:
            self.client = QdrantClient(url=url)
        elif path:
            self.client = QdrantClient(path=path)
        else:
            self.client = QdrantClient(location=location)
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE)
            )

    @staticmethod
    def _pid(chunk_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        m = self._models
        points = [
            m.PointStruct(id=self._pid(c.id), vector=list(v),
                          payload={"chunk_id": c.id, "text": c.text, "source": c.source,
                                   "heading": c.heading, **c.metadata})
            for c, v in zip(chunks, vectors)
        ]
        self.client.upsert(self.collection, points=points)

    def search(self, vector: Sequence[float], k: int, filters: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        m = self._models
        qf = None
        if filters:
            qf = m.Filter(must=[m.FieldCondition(key=key, match=m.MatchValue(value=val))
                                for key, val in filters.items()])
        res = self.client.query_points(self.collection, query=list(vector), limit=k,
                                       query_filter=qf, with_payload=True).points
        out = []
        for r in res:
            p = dict(r.payload or {})
            out.append(Chunk(id=p.pop("chunk_id"), text=p.pop("text"), source=p.pop("source", ""),
                             heading=p.pop("heading", ""), score=float(r.score), metadata=p))
        return out
