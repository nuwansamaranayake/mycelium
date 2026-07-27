# Evaluation — Mycelium

Releases are gated on measured behavior, not vibes. This file defines *what good means* for Mycelium
and how `make eval` will measure it. The targets below are acceptance criteria the Phase-1 harness
will enforce; they are **goals, not achieved results**.

> **Status: the harness is real as of Phase 1.** `scripts/eval.py` enforces the threshold table
> below as a required CI check (first published run 2026-07-27, all bounds PASS —
> `eval_report.md`, byte-reproducible). Its first run caught three real retrieval defects
> before they reached a user (FAILURES.md FAIL-0005). The key-gated synthesis section
> (`scripts/eval_llm.py`) observed citation coverage 1.00 and grounding validity 1.00 through
> the real gateway (`eval_report_llm.md`).

## Phase 1 acceptance thresholds (written before the harness, 2026-07-27)

Phase 1 ships the keyless retrieval product (folder + upload connectors, hybrid BM25 + cosine
retrieval with rank fusion, query-time ACL enforcement, citations with deterministic freshness
labels), so its bounds measure retrieval, access control, citation integrity, and temporal
labeling. The suite is deterministic and keyless: a golden synthetic corpus (~10 documents with
planted timestamps and ACLs), labeled queries with pre-authored paraphrase sets, planted
restricted-principal cases, and the deterministic HashingEmbedder keep it byte-reproducible as a
required CI check. `scripts/eval.py` exits nonzero on any miss.

| Metric | Definition | Bound |
|---|---|---|
| Retrieval hit@3 | labeled queries whose expected document appears in the top-3 fused results | >= 0.85 |
| ACL leak rate | results surfaced to a restricted principal from a document it may not see (planted adversarial cases) | = 0 |
| Citation validity | every cited passage exists and the document text at the cited span equals the passage text | = 1.00 |
| Freshness label correctness | fresh/aging/stale labels versus planted timestamps at the corpus reference time | = 1.00 |
| Retrieval stability | Jaccard of retrieved doc-id sets between each query and its pre-authored paraphrases | >= 0.60 |
| Reproducibility | two consecutive `make eval` runs | identical reports |

Staleness math never calls `datetime.now()` in the eval path: the reference time is part of the
golden corpus and part of the query request; only the live API defaults it to now.

Answer synthesis (LLM stage) is measured separately and key-gated (`scripts/eval_llm.py`):
every generated sentence must cite a retrieved passage id (citation coverage = 1.00) and every
cited id must be one of the passages actually retrieved (grounding validity = 1.00), through
the real gateway. Reported when a key is present, never a required keyless check, and never
silently skipped: the report states loudly when the key-gated section did not run. The
retrieval-stability invariant is also declared as a Seismograph behavioral contract in
`contracts/retrieval-stability.yaml`.

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
