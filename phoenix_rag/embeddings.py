"""Deterministic, dependency-free embedder (signed feature hashing).

Good enough for exact-vocabulary matches on error names and function names
(the dominant signal for stack-trace -> guideline lookup). Swap in a real
model by implementing `Embedder` -- nothing else changes.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import List

_SPLIT_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_TOKEN = re.compile(r"[A-Za-z0-9]+")
_STOP = frozenset(
    "a an and are as at be by for from has have in is it of on or that the this to was were will with "
    "you your we our not if then else when do does use used using can should must".split()
)


def tokenize(text: str) -> List[str]:
    toks: List[str] = []
    for raw in _TOKEN.findall(text.replace("_", " ")):
        for part in _SPLIT_CAMEL.sub(" ", raw).split():
            p = part.lower()
            if p not in _STOP and len(p) > 1:
                toks.append(p)
    return toks


class HashingEmbedder:
    def __init__(self, dim: int = 512):
        self.dim = dim

    def _slot(self, feature: str) -> tuple[int, float]:
        h = int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "big")
        return h % self.dim, (1.0 if (h >> 63) & 1 else -1.0)

    def embed(self, text: str) -> List[float]:
        toks = tokenize(text)
        feats: dict[str, float] = {}
        for t in toks:
            feats[t] = feats.get(t, 0.0) + 1.0
        for a, b in zip(toks, toks[1:]):
            key = f"{a}_{b}"
            feats[key] = feats.get(key, 0.0) + 0.5
        vec = [0.0] * self.dim
        for f, tf in feats.items():
            idx, sign = self._slot(f)
            vec[idx] += sign * (1.0 + math.log(tf))
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
