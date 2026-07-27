# LOOP_STATE — Mycelium Phase 1

Branch: `phase-1`. Goal: the Phase 1 core loop — two keyless connectors (folder ingester +
direct API upload), hybrid retrieval (BM25 + embedding cosine, rank-fused), per-document ACLs
enforced at query time, cited answers with deterministic freshness labels, and a key-gated
LLM answer-synthesis stage through the groundwork gateway.

## Milestones

- [x] M1 branch `phase-1` + LOOP_STATE.md + EVAL.md acceptance bounds (written before the harness)
- [x] M2 engine modules (embedding, chunking, freshness, retrieval, synthesis) with tests
- [x] M3 golden corpus + deterministic keyless eval harness meeting the pre-written bounds
      (first run failed 2 bounds, found 3 real defects — FAILURES.md FAIL-0005; all PASS now)
- [x] M4 schema + alembic 0002 + API routes + CLI + smoke test (MIGRATION OK: 9; SMOKE OK)
- [x] M5 contracts/retrieval-stability.yaml validated against Seismograph's contract DSL
      (plan_id 6601551bb7660392, 6 entries, loader run from the Seismograph repo)
- [x] M6 key-gated eval_llm observed: citation coverage 1.00, grounding validity 1.00
- [x] M7 CI eval job flipped to "eval (required)" + docs truth pass (README, contracts.md,
      CHANGELOG, EVAL.md status, FAILURES.md FAIL-0004/0005/0006)
- [ ] FINAL gate.py GATE OK + check_migrations MIGRATION OK + prod-guard + byte-reproducibility

## DECISION

- Tables (8 app + alembic_version = 9): documents, passages, principals, acl_entries,
  queries, retrievals, answers, answer_citations. EXPECTED_TABLE_COUNT=9.
- Rank fusion: reciprocal rank fusion (k=60) over the BM25 ranking and the cosine ranking,
  deterministic tie-break on passage id.
- Freshness labels (deterministic, from ingest-supplied timestamps vs a reference time
  carried by the request; datetime.now() only as the live-API default): fresh < 30 days,
  aging 30 to 180 days, stale > 180 days.
- ACL model: acl_entries rows per document; `*` means every principal. Filtering happens
  before scoring, so a forbidden passage never enters the candidate set.
- Embedders: HashingEmbedder (deterministic, keyless, dim=4096) and OpenRouterEmbedder,
  copied from CareerCompiler; the caller always names which one it wants.

## BLOCKED

(none)

## Next

M2: engine modules with tests.
