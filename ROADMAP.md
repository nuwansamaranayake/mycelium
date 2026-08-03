# Roadmap — Mycelium

Three phases, following the BLUEPRINT MVP build path. Each phase mirrors a GitHub Milestone and its
issues are tracked on the public project board; a phase is done only when its `make eval` thresholds
(see `EVAL.md`) pass and the smoke test hits real endpoints.

## Phase 1 — Retrieval with trust labels

*Mirrors GitHub Milestone "Phase 1 — Retrieval".*

The honest read path first.

- Connectors for one wiki and one chat tool (ingestion, chunking — deterministic).
- Hybrid retrieval (BM25 + vectors) with ACL enforcement applied at query time, before any chunk
  reaches model context.
- Cited answers with freshness labels: LLM synthesis with mandatory citations; deterministic
  freshness scoring and the warranty label attached by code.
- Eval harness stood up (replaces the intentional `NotImplementedError`): recall@k, citation
  precision, and a zero-ACL-leakage adversarial test.

## Phase 2 — partial (2026-08-03, honest status)

**Shipped:** credential-less demo sessions on the shared estate kit (scoped, budgeted,
expiring; tenant-prefixed rows swept by the estate retention), the frontend (principal
switcher, pre-scoring ACL exclusion counts on screen, freshness chips, honest misses,
cited synthesis with ungrounded sentences flagged), demo-scoped PDF/docx upload, and the
wildcard-ACL carve-out for demo tenants (found by the local E2E: a "*" grant must not
reach a demo visitor).

**Not built, deliberately named:** the self-healing loop — per-query telemetry, demand-
ranked gap tickets, owner routing over the ownership graph, approval-gated patches. That
is the product's novelty claim and it remains future work; nothing on the live page
implies otherwise.

## Phase 3 — Bitemporal memory + conflict honesty

*Mirrors GitHub Milestone "Phase 3 — Bitemporal".*

- Bitemporal claim store with as-of and changed-since queries; corrections close-and-open, never
  overwrite.
- Conflict detection with the `NEEDS_RESOLUTION` state (NLI-assisted contradiction judgment,
  deterministic materiality trigger).
- Per-type decay clocks, owner-overridable and recalibrated against observed edit frequency.
- Consent-gated Slack capture: threads that answered what search missed become drafted, approvable
  entries.
- Corpus-health dashboard: staleness burn-down, gap-closure time, warranty calibration.
