# Truth layer — Mycelium public frontend (pre-deploy, 2026-08-03)

Rule: no claim on the page that the evals do not support. Canonical facts with evidence.

| Fact | Evidence |
|---|---|
| The ACL filter runs BEFORE retrieval scoring; a restricted principal's excluded documents are counted from the same set retrieval filters on | `app/engine/retrieval.py` (`allowed_doc_ids` first), `/query` acl block; `test_the_restricted_principal_cannot_retrieve_the_restricted_document` |
| Measured on the golden corpus: **0 ACL leaks; citation validity 1.0; freshness label accuracy 1.0; paraphrase jaccard 1.0** (bound 0.60). The corpus is synthetic — recall on a real knowledge base is not measured | EVAL.md LIMITS block, rendered verbatim on the landing (gate asserts) |
| Freshness labels are computed by deterministic date arithmetic, never by the model | `app/engine/freshness.py` docstring + eval 1.0 |
| An off-corpus question returns zero passages and the UI says so; no fluent guess. Synthesis is never called on empty retrievals (422 backstop) | measured 2026-08-03: parental-leave + nonsense queries → `results: []`; `/answers` 422 on empty |
| Ungrounded sentences in a synthesized answer are counted and flagged, not hidden | `/answers` returns `ungrounded_count` + per-sentence `grounded` |
| Demo principals are real principals with real bearer tokens on the production auth path; the switcher changes which bearer is sent | `test_principal_tokens_are_real_auth_not_demo_semantics` |
| Demo data synthetic and labelled; demo rows deleted by the retention sweep once older than 7 days | seed titles/names prefix-shaped; portfolio-ops sweep covers `demo-` (proven by row count on production for CC; mycelium drill due at G) |

## Banned / scoped phrasing

- The PRD novelty claim is **scoped to a July 2026 survey** — keep "of the tools we
  reviewed as of July 2026" on the page; never a universal "the only" claim.
- No "zero hallucination", no "guarantees": say "flags ungrounded sentences" and "refuses
  when retrieval returns nothing".
- "self-healing" is roadmap (Part E not shipped): the page may name it only as planned.

## Wedge

**"RAG that shows you what it refused to read."** The demo moment is switching principals
and watching the restricted document leave both the answer and the sources, with the
exclusion counted before scoring.
