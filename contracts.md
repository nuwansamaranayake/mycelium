# API Contracts — Mycelium

Doctrine Standard 6: every frontend call maps to exactly one backend endpoint, and this file is
diffed in CI against the live OpenAPI spec at `/openapi.json` (FastAPI also serves interactive docs
at `/docs`). The frontend is a Next.js app arriving in Phase 2; the "Frontend call (Phase 2)" column
names the call it *will* make, so the mapping is reviewable before the UI exists. A call with no
backend endpoint, or an endpoint whose shape drifts from this table, is a CI failure.

| Frontend call (Phase 2) | Method | Path | Status | Notes |
|---|---|---|---|---|
| Liveness/readiness probe | `GET` | `/health` | implemented | Returns `{status, env}`. No auth. Used by smoke test and orchestration. |
| Demo fixture view | `GET` | `/api/v1/demo` | implemented | Returns `{items: [...]}` from `data/synthetic/`. Development-only; returns **503** outside `development`. Smoke test asserts `items` non-empty. |
| API schema | `GET` | `/openapi.json`, `/docs` | implemented | OpenAPI spec + Swagger UI, served by FastAPI. This file is diffed against it. |
| Ask a question (current / as-of / changed-since) | `POST` | `/api/v1/query` | planned — Phase 1 | Body carries the query, requester identity, and optional `as_of` date. Returns an answer, mandatory citations, warranty label, valid period, and state (`ANSWERED` / `BEST_AVAILABLE` / `NEEDS_RESOLUTION`). ACL-filtered before generation. |
| Fetch a conflict for resolution | `GET` | `/api/v1/conflicts/{id}` | planned — Phase 3 | Returns both claims, their authority and dates, and the owner asked to reconcile. Backs the `NEEDS_RESOLUTION` UI. |
| List gap tickets (owner inbox) | `GET` | `/api/v1/gap-tickets` | planned — Phase 2 | Demand-ranked tickets routed to the authenticated owner; supports reassign. |
| Approve / edit / reject a patch proposal | `POST` | `/api/v1/patches/{id}/decision` | planned — Phase 2 | Human approval gate. On approval, writes a bitemporal claim with provenance and a reset warranty. No write without this decision. |
| As-of / changed-since history for a claim | `GET` | `/api/v1/claims/{id}/history` | planned — Phase 3 | Bitemporal record: `valid_from`/`valid_to` and `recorded_at`/`superseded_at`. Corrections close-and-open, never overwrite. |
