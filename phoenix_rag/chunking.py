"""Markdown-aware chunker: split on headings, keep code fences intact,
then pack paragraphs up to `max_chars` with a small overlap."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, List, Tuple

from phoenix_contracts import Chunk

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def _sections(text: str) -> List[Tuple[str, str]]:
    """Return [(heading, body)] splitting on markdown headings outside code fences."""
    sections: List[Tuple[str, List[str]]] = [("", [])]
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m:
            sections.append((m.group(2), []))
        else:
            sections[-1][1].append(line)
    return [(h, "\n".join(b).strip()) for h, b in sections if "\n".join(b).strip()]


def _blocks(body: str) -> List[str]:
    """Paragraph-level blocks; a fenced code block is a single block."""
    blocks, buf, in_fence = [], [], False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            buf.append(line)
            if not in_fence:
                blocks.append("\n".join(buf)); buf = []
            continue
        if not in_fence and not line.strip():
            if buf:
                blocks.append("\n".join(buf)); buf = []
        else:
            buf.append(line)
    if buf:
        blocks.append("\n".join(buf))
    return blocks


def chunk_markdown(text: str, source: str, max_chars: int = 900, overlap_blocks: int = 1) -> List[Chunk]:
    chunks: List[Chunk] = []
    for heading, body in _sections(text):
        blocks = _blocks(body)
        i = 0
        while i < len(blocks):
            cur, size, j = [], 0, i
            while j < len(blocks) and (not cur or size + len(blocks[j]) <= max_chars):
                cur.append(blocks[j]); size += len(blocks[j]) + 2; j += 1
            body_text = "\n\n".join(cur)
            prefix = f"{heading}\n" if heading else ""
            cid = hashlib.sha1(f"{source}|{heading}|{body_text}".encode()).hexdigest()[:16]
            chunks.append(Chunk(id=cid, text=prefix + body_text, source=source, heading=heading,
                                metadata={"source": source, "heading": heading}))
            if j >= len(blocks):
                break
            i = max(j - overlap_blocks, i + 1)   # always make progress
    return chunks


def chunk_paths(paths: Iterable[Path], **kw) -> List[Chunk]:
    out: List[Chunk] = []
    for p in paths:
        out.extend(chunk_markdown(p.read_text(encoding="utf-8"), source=p.name, **kw))
    return out
