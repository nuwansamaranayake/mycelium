# Evaluation — Mycelium

Releases are gated on measured behavior, not vibes. This file defines *what good means* for Mycelium
and how `make eval` will measure it. The targets below are acceptance criteria the Phase-1 harness
will enforce; they are **goals, not achieved results**.

> **Status: the eval harness raises `NotImplementedError` on purpose.** No numbers are reported yet.
> The scoring code and labeled fixtures land in Phase 1 (see `ROADMAP.md`); until then, `make eval`
> fails loudly rather than printing a fabricated pass. That is the doctrine, not an oversight.

## What good means

Mycelium is good when a served answer is honest about how much to trust it, when its access control
never leaks, when it remembers what was true when, and when it refuses to blend sources that
materially disagree. Retrieval quality is necessary but not sufficient — the differentiating metrics
are about corpus health and temporal honesty, which incumbents do not report.

## How `make eval` will measure it

Mapped to the BLUEPRINT "How It Is Evaluated":

- **Retrieval quality** — recall@k and citation precision on a labeled query set. An answer whose
  citations do not support its claims fails, regardless of fluency.
- **ACL leakage — target zero, tested adversarially.** A red-team query set attempts to retrieve
  chunks the querying identity may not see. Any leak is a release blocker, not a warning. ACL
  filtering is enforced at retrieval time, before generation.
- **As-of answer correctness** — a versioned synthetic corpus with known history is queried at past
  dates; answers must match what was true then, not the current record.
- **Conflict-detection precision** — planted contradictions between high-authority sources must
  trigger `NEEDS_RESOLUTION` rather than a blended average; measured as precision on the planted set.
- **Warranty calibration** — are owner-verified answers accepted measurably more often than
  best-available ones? Calibration is checked against acceptance telemetry, not asserted.
- **Corpus-health loop metrics** — gap-closure time and staleness burn-down, tracked release over
  release once the healing loop (Phase 2) exists.

## Published reports

Per the Governed Repo Standard, each release publishes its eval report alongside the tag. Seismograph
(App 1) additionally probes answer consistency and citation faithfulness continuously between
releases, so drift is caught outside the release cadence. Until Phase 1 lands the scoring code, the
only honest report is this one: *not yet measured.*
