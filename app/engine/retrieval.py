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

# A passage surfaces only when at least one signal clears this fraction of the best hit.
# Without the floor, top-k is padded with weak-evidence stragglers whose identity flips
# under paraphrase (observed: doc-set jaccard 0.5 with the correct doc stable at rank 1 —
# see FAILURES.md). Returning junk to fill k is the dishonesty this product refuses.
RELEVANCE_FLOOR = 0.5

# Function words carry no retrieval signal but fabricate cosine similarity between any two
# English texts (observed: eval stability_min 0.0 before filtering — see FAILURES.md).
# BM25's IDF already downweights them; the bag-of-tokens embedding leg does not, so both
# legs score on content tokens only.
STOPWORDS = frozenset(
    "a an and are as at be but by do does down for from how i in is it its my of on or our "
    "the their this to up was we what when where which who will with you your".split())


class CorpusPassage(BaseModel):
    """One retrievable unit. `doc_id` carries the ACL; `span` makes the citation checkable.
    `title` is the document title, indexed for scoring (a runbook whose body never says
    "runbook" must still match) but never part of the cited span."""
    passage_id: str
    doc_id: str
    text: str
    span_start: int
    span_end: int
    title: str = ""


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


def _content_tokens(text: str) -> list[str]:
    toks = [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]
    # an all-stopword query still deserves an answer set: fall back to raw tokens
    return toks or _TOKEN.findall(text.lower())


def _scoring_text(p: CorpusPassage) -> str:
    return " ".join(_content_tokens(f"{p.title} {p.text}"))


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

    q_tokens = _content_tokens(query)
    bm25 = BM25Okapi([_content_tokens(f"{p.title} {p.text}") for p in candidates])
    bm25_scores = list(bm25.get_scores(q_tokens))

    vectors = embedder.embed([_scoring_text(p) for p in candidates])
    [q_vec] = embedder.embed([" ".join(q_tokens)])
    cos_scores = [cosine(q_vec, v) for v in vectors]

    best_bm25 = max(bm25_scores)
    best_cos = max(cos_scores)
    kept = [i for i in range(len(candidates))
            if (best_bm25 > 0 and bm25_scores[i] >= RELEVANCE_FLOOR * best_bm25)
            or (best_cos > 0 and cos_scores[i] >= RELEVANCE_FLOOR * best_cos)]
    if not kept:  # nothing clears the floor (e.g. no signal at all): honest empty set
        return []

    def ranking(scores: list[float]) -> dict[str, int]:
        order = sorted(kept, key=lambda i: (-scores[i], candidates[i].passage_id))
        return {candidates[i].passage_id: rank for rank, i in enumerate(order)}

    bm25_rank = ranking(bm25_scores)
    cos_rank = ranking(cos_scores)

    fused = []
    for i in kept:
        p = candidates[i]
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
