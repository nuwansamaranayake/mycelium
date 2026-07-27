"""Deterministic passage chunking: paragraphs with exact character spans.

A document splits on blank lines into passages. Every passage records its (start, end) span
into the source text and the invariant text == document_text[start:end] holds by
construction, so a citation is verifiable by a substring check — no fuzzy matching, no
re-chunking drift between ingest and eval.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

_PARA_SPLIT = re.compile(r"\n\s*\n")


class PassageChunk(BaseModel):
    ordinal: int
    text: str
    span_start: int
    span_end: int


def chunk_document(text: str) -> list[PassageChunk]:
    """Split into paragraph passages. Whitespace-only paragraphs are skipped; spans are
    trimmed to the stripped paragraph so the substring invariant holds exactly."""
    chunks: list[PassageChunk] = []
    cursor = 0
    ordinal = 0
    for raw in _PARA_SPLIT.split(text):
        start = text.index(raw, cursor)
        cursor = start + len(raw)
        stripped = raw.strip()
        if not stripped:
            continue
        inner = start + raw.index(stripped)
        chunks.append(PassageChunk(
            ordinal=ordinal, text=stripped,
            span_start=inner, span_end=inner + len(stripped)))
        ordinal += 1
    return chunks
