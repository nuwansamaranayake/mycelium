# Changelog

All notable changes to Mycelium are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 1 core loop (branch `phase-1`): two keyless connectors (folder ingester with optional
  `manifest.json`, direct `POST /api/v1/documents` upload), hybrid retrieval (BM25 + embedding
  cosine, reciprocal rank fusion with a relevance floor), per-document ACLs enforced before any
  scoring, and citations (document id + exact span) with deterministic freshness labels
  computed against the request's `as_of` (wall-clock only as the live-API default).
- Real schema (8 app tables + `alembic_version` = 9; `EXPECTED_TABLE_COUNT=9`) applied by
  alembic `0002_real_schema` from `app.db.metadata`; Dockerfile migrates and asserts the count
  before serving. Observed: `MIGRATION OK: 9 tables`.
- Key-gated answer synthesis (`POST /api/v1/answers`) through the groundwork gateway with a
  strict JSON schema; deterministic citation audit per sentence; typed 503 without
  `OPENROUTER_API_KEY`.
- Deterministic keyless eval (`scripts/eval.py`, required in CI). Observed on the golden
  corpus: retrieval hit@3 1.0, ACL leak count 0, citation validity 1.0, freshness correctness
  1.0, paraphrase stability (min jaccard) 1.0, byte-reproducible report.
- Key-gated synthesis eval (`scripts/eval_llm.py`). Observed via the real gateway
  (anthropic/claude-sonnet-5): citation coverage 1.00, grounding validity 1.00.
- Seismograph behavioral contract `contracts/retrieval-stability.yaml`, validated against the
  Seismograph contract DSL (plan_id `6601551bb7660392`, 6 plan entries).
- CLI (`python -m app.cli query`): keyless, serverless retrieval over a golden-format corpus.
- 19 pytest cases: engine invariants (span-exact chunking, freshness thresholds, ACL
  deny-by-default, determinism) and the API loop on an injected sqlite engine with a stub
  gateway. No network in tests.

### Changed
- CI eval job flipped to `eval (required)` (continue-on-error removed) with lean keyless deps.
- Smoke test now exercises the full keyless loop: principals, upload, folder ingest, permitted
  and forbidden queries (ACL probe with verbatim document text).

### Changed (scaffold era)
- Dependency on `aignite-groundwork` switched from an editable path source to a pinned git
  dependency (`git+https://github.com/nuwansamaranayake/groundwork@v0.1.0`) so standalone clones and CI resolve
  it without a sibling checkout. PyPI publication planned at first release.
- `scripts/check_migrations.py` now uses `DATABASE_URL` with the declared psycopg v3 driver
  unmodified, fixing a clean-machine `make migrate` failure (see FAILURES.md FAIL-0002).
- README truth pass: scaffold status block, `(the design)` heading, "What exists today (verified)"
  section, scoped/dated novelty, dual-path Quickstart, em-dash sweep.
- CI: Python matrix (3.12, 3.13); eval job labeled "eval (Phase 1 pending)".

### Added
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) and a SECURITY.md vulnerability-reporting policy.

## [0.1.0] - 2026-07-21
### Added
- Engineering harness scaffold: governed doc set, config guard, verification gates,
  smoke test against a real business endpoint, migration-count check, CI pipeline,
  and a synthetic dataset so the demo runs with zero external keys.
