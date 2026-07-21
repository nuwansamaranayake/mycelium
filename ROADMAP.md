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

## Phase 2 — The healing loop + first UI

*Mirrors GitHub Milestone "Phase 2 — Healing loop".*

Close the write path end to end on one team, and ship the interface.

- Telemetry scoring of every query (was retrieval confident, did sources agree, was evidence fresh,
  did the user accept the answer?).
- Gap-ticket generator: failed and low-confidence queries aggregate into demand-ranked tickets.
- Owner routing over a deterministic ownership graph, with one-click reassign and per-owner rate
  limits.
- Approval-gated patches: the LLM drafts from the owner's reply; nothing enters the corpus without
  human sign-off.
- **Next.js frontend** (the one shared portfolio design system): the answer + warranty-label UI, the
  gap-ticket inbox for owners, and the three-question demo view. This is the phase the UI arrives —
  earlier phases are API-only.

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
