"""Hybrid retrieval: BM25 + embedding cosine, reciprocal-rank fused, ACL-filtered first.

The access check runs before any scoring: a passage whose document the principal may not
see never enters the candidate set, so it cannot leak through a score, a rank, or a cache.
Fusion is reciprocal rank fusion (k=60) over the two independent rankings with a
deterministic tie-break on passage id — with the HashingEmbedder the whole pipeline is
byte-reproducible.
"""
from __future__ import annotations

import re

from pydantic import BaseModel
from rank_bm25 import BM25Okapi

from .embedding import Embedder, cosine

_TOKEN = re.compile(r"[a-z0-9]+")
RRF_K = 60


class CorpusPassage(BaseModel):
    """One retrievable unit. `doc_id` carries the ACL; `span` makes the citation checkable."""
    passage_id: str
    doc_id: str
    text: str
    span_start: int
    span_end: int


class RetrievedPassage(BaseModel):
    passage_id: str
    doc_id: str
    rank: int
    bm25_score: float
    cosine_score: float
    fused_score: float


def allowed_doc_ids(principal: str, acls: dict[str, set[str]]) -> set[str]:
    """Documents the principal may see. `*` grants every principal; a document with no ACL
    entry is private by default — absence never grants access."""
    if not principal:
        raise ValueError("query carries no principal; refusing to retrieve without identity")
    return {doc_id for doc_id, who in acls.items() if "*" in who or principal in who}


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def retrieve(
    query: str,
    passages: list[CorpusPassage],
    principal: str,
    acls: dict[str, set[str]],
    embedder: Embedder,
    top_k: int = 5,
) -> list[RetrievedPassage]:
    visible = allowed_doc_ids(principal, acls)
    candidates = sorted(
        (p for p in passages if p.doc_id in visible), key=lambda p: p.passage_id)
    if not candidates:
        return []

    q_tokens = _tokens(query)
    bm25 = BM25Okapi([_tokens(p.text) for p in candidates])
    bm25_scores = list(bm25.get_scores(q_tokens))

    vectors = embedder.embed([p.text for p in candidates])
    [q_vec] = embedder.embed([query])
    cos_scores = [cosine(q_vec, v) for v in vectors]

    def ranking(scores: list[float]) -> dict[str, int]:
        order = sorted(range(len(candidates)),
                       key=lambda i: (-scores[i], candidates[i].passage_id))
        return {candidates[i].passage_id: rank for rank, i in enumerate(order)}

    bm25_rank = ranking(bm25_scores)
    cos_rank = ranking(cos_scores)

    fused = []
    for i, p in enumerate(candidates):
        score = (1.0 / (RRF_K + bm25_rank[p.passage_id])
                 + 1.0 / (RRF_K + cos_rank[p.passage_id]))
        fused.append((score, p, bm25_scores[i], cos_scores[i]))
    fused.sort(key=lambda t: (-t[0], t[1].passage_id))

    return [
        RetrievedPassage(
            passage_id=p.passage_id, doc_id=p.doc_id, rank=rank,
            bm25_score=round(b, 6), cosine_score=round(c, 6), fused_score=round(s, 6))
        for rank, (s, p, b, c) in enumerate(fused[:top_k])
    ]
