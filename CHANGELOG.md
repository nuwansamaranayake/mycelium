# Changelog

All notable changes to Mycelium are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-07-23

### Removed
- Unused `sentence-transformers` dependency (and the CUDA torch stack it pulled). No Phase 1
  code imports it; production images drop from ~5.7 GB toward the ~0.5 GB baseline
  (FAILURES FAIL-0010).

### Security
- Adversarial review wave (15 confirmed findings, MYC-001..015) fixed before release:
  - `GET /api/v1/answers/{id}` is no longer unauthenticated: read-back requires the
    originating query's principal token (or the admin token) when auth is armed —
    restricted corpus content can no longer be read by guessing sequential ids.
  - Query identity now binds to a credential: registration issues a per-principal bearer
    token (`principals.token`, alembic `0003_principal_tokens`), and `/api/v1/query`
    derives the principal from it (403 on body/credential mismatch, 401 for unknown or
    admin tokens) instead of trusting the request body.
  - Auth no longer fails open: an empty `SMOKE_TEST_TOKEN` turns auth off in development
    only; staging/production get a typed 503 naming the variable.
  - The folder connector is confined to a configured `INGEST_ROOT` (default `data`);
    paths resolving outside it are a typed 422 instead of an arbitrary local-directory
    read into the datastore.
  - Added `.dockerignore` so `COPY . .` no longer bakes `.env` (live key material) and
    `.git` history into image layers.

### Fixed
- LLM/network calls no longer run inside open DB transactions: `/api/v1/query` and
  `/api/v1/answers` load inputs in a short read session, call the embedder/gateway with no
  transaction open, then write in a second short transaction (no more pool starvation
  during 60s LLM round-trips).
- Empty synthesis (zero sentences) is a typed `EmptySynthesisError` surfaced as 502 and
  never persisted; previously it was recorded as a "perfectly grounded" empty answer with
  `ungrounded_count=0`. The JSON schema now sets `minItems: 1`.
- Principal registration is race-safe: insert-first with the unique constraint as the
  arbiter (concurrent duplicate registration returns the idempotent response instead of a
  500 `IntegrityError`).
- Tokenization is Unicode-aware in both retrieval legs (`[^\W_]+` replaces ASCII-only
  `[a-z0-9]+`): Cyrillic/Greek/CJK/Arabic content is retrievable and accented Latin terms
  are no longer truncated. A Cyrillic document/query pair was added to the golden corpus.
- `scripts/eval.py` stability scoring no longer reports a dead labeled query (empty
  retrieval) as perfectly stable via the empty-empty Jaccard convention; it scores 0.0.
- `scripts/check_migrations.py` refuses to print `MIGRATION OK` when
  `EXPECTED_TABLE_COUNT` is unset or 0 (`MIGRATION CHECK NOT ARMED`, exit 1).
- `scripts/smoke_test.py` now branches on `/health`'s env: outside development it asserts
  the demo fixture 503s and still runs every business assertion, so the smoke gate works
  against staging/production; with auth armed it also asserts impersonation is refused.
- `/api/v1/query` with `embedder=openrouter` and missing `OPENROUTER_API_KEY` /
  `EMBEDDING_MODEL` returns a typed 503 naming the variable, matching the `/answers` path.
- Engine/session lazy init is guarded by a lock and gated on the fully initialized state
  (no cold-start race creating duplicate pools or observing a half-built session factory).
- README quickstart smoke commands export `SMOKE_TEST_TOKEN=dev-smoke-token`, matching
  `.env.example`, so following the quickstart verbatim yields `SMOKE OK` instead of 401.

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
