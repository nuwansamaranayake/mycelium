# API Contracts — Mycelium

Doctrine Standard 6: every frontend call maps to exactly one backend endpoint, and this file is
diffed in CI against the live OpenAPI spec at `/openapi.json` (FastAPI also serves interactive docs
at `/docs`). The frontend is a Next.js app arriving in Phase 2; the "Frontend call (Phase 2)" column
names the call it *will* make, so the mapping is reviewable before the UI exists. A call with no
backend endpoint, or an endpoint whose shape drifts from this table, is a CI failure.

| Frontend call (Phase 2) | Method | Path | Status | Notes |
|---|---|---|---|---|
| Front page (browser) | GET | `/` | none | Self-contained HTML: thesis, what it measures, the EVAL.md limits sentence, the endpoint list, build stamp. Public by design. |
| Liveness/readiness probe | `GET` | `/health` | implemented | Returns `{status, env}`. No auth. Used by smoke test and orchestration. |
| Demo fixture view | `GET` | `/api/v1/demo` | implemented | Returns `{items: [...]}` from `data/synthetic/`. Development-only; returns **503** outside `development`. Smoke test asserts `items` non-empty. |
| API schema | `GET` | `/openapi.json`, `/docs` | implemented | OpenAPI spec + Swagger UI, served by FastAPI. This file is diffed against it. |
| Register a principal | `POST` | `/api/v1/principals` | implemented | Body `{name}`. Idempotent on name (unique-constraint arbitrated — race-safe). Returns `{principal_id, created, token}`: the per-principal bearer token that `/api/v1/query` and answer read-back authenticate with. Admin bearer auth (`SMOKE_TEST_TOKEN`) when set. |
| Upload a document (direct connector) | `POST` | `/api/v1/documents` | implemented | Body `{title, text, doc_timestamp, allowed_principals, external_id?}`. Timestamp must carry a timezone (422 otherwise). Chunks into span-anchored passages, stores ACL entries. Keyless product path. |
| Ingest a folder (filesystem connector) | `POST` | `/api/v1/ingest/folder` | implemented | Body `{path}`. Reads `.txt`/`.md` files plus optional `manifest.json` (title, timestamp, ACLs per file; private by default without a manifest entry). The path must resolve inside the configured `INGEST_ROOT` (default `data`); anything else is **422**. Keyless product path. |
| Ask a question (retrieval) | `POST` | `/api/v1/query` | implemented | Body `{principal, query, top_k?, as_of?, embedder?}`. Identity binds to the credential: with auth armed the bearer token must be the principal's own registration token and match `principal` (**401**/**403** otherwise); with auth off (development only) the body principal is trusted. ACL-filtered before scoring; hybrid BM25 + cosine with reciprocal rank fusion and a relevance floor. Each result cites document id + span and carries a freshness label computed against `as_of` (defaults to now only here, the live API). Persists the query and its retrievals. |
| Synthesize a cited answer | `POST` | `/api/v1/answers` | implemented | Body `{query_id}`. Key-gated: typed **503** naming `OPENROUTER_API_KEY` when absent. Every sentence must cite retrieved passage ids; deterministic code audits citations and counts ungrounded sentences. An empty synthesis (zero sentences) is a typed **502**, never recorded. Persists answer + citations. |
| Fetch a stored answer | `GET` | `/api/v1/answers/{id}` | implemented | Returns the answer row and its citations (sentence index, passage id, sentence text). Read-back is gated: with auth armed the bearer token must be the originating query's principal token (or the admin token); **401**/**403** otherwise. |
| Intent classification (current / as-of / changed-since) and warranty labels | `POST` | `/api/v1/query` (extension) | planned — Phase 3 | Warranty labels (authority x corroboration) and `NEEDS_RESOLUTION` state extend the query response when trust scoring lands. Freshness labels are the Phase 1 slice. |
| Fetch a conflict for resolution | `GET` | `/api/v1/conflicts/{id}` | planned — Phase 3 | Returns both claims, their authority and dates, and the owner asked to reconcile. Backs the `NEEDS_RESOLUTION` UI. |
| List gap tickets (owner inbox) | `GET` | `/api/v1/gap-tickets` | planned — Phase 2 | Demand-ranked tickets routed to the authenticated owner; supports reassign. |
| Approve / edit / reject a patch proposal | `POST` | `/api/v1/patches/{id}/decision` | planned — Phase 2 | Human approval gate. On approval, writes a bitemporal claim with provenance and a reset warranty. No write without this decision. |
| As-of / changed-since history for a claim | `GET` | `/api/v1/claims/{id}/history` | planned — Phase 3 | Bitemporal record: `valid_from`/`valid_to` and `recorded_at`/`superseded_at`. Corrections close-and-open, never overwrite. |
