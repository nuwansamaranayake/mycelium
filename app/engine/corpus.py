"""In-memory corpus assembly from golden-format document dicts.

Shared by the CLI, the eval harness, and tests so they all exercise the same chunking and
ACL construction the API uses — one corpus builder, no parallel implementations to drift.
"""
from __future__ import annotations

from datetime import datetime

from .chunking import chunk_document
from .retrieval import CorpusPassage


def build_corpus(
    documents: list[dict],
) -> tuple[list[CorpusPassage], dict[str, set[str]], dict[str, datetime]]:
    """documents: [{doc_id, text, allowed_principals, timestamp}, ...] ->
    (passages, acls, timestamps). Timestamps must be ISO-8601 with timezone."""
    passages: list[CorpusPassage] = []
    acls: dict[str, set[str]] = {}
    timestamps: dict[str, datetime] = {}
    for doc in documents:
        doc_id = doc["doc_id"]
        if doc_id in acls:
            raise ValueError(f"duplicate doc_id {doc_id!r} in corpus")
        acls[doc_id] = set(doc["allowed_principals"])
        ts = doc["timestamp"]
        timestamps[doc_id] = ts if isinstance(ts, datetime) else datetime.fromisoformat(ts)
        for chunk in chunk_document(doc["text"]):
            passages.append(CorpusPassage(
                passage_id=f"{doc_id}#p{chunk.ordinal}", doc_id=doc_id,
                text=chunk.text, span_start=chunk.span_start, span_end=chunk.span_end,
                title=doc.get("title", "")))
    return passages, acls, timestamps
