# PRD — Mycelium

## Users

- **Knowledge seeker** (any employee). Asks a question and needs an answer they can trust and cite,
  not a fluent paragraph of unknown vintage. Cares about correctness, freshness, and "is this still
  true?"
- **Document owner** (the person who actually knows a policy, service, or process). Receives routed
  gap tickets as one-question micro-requests, approves or edits drafted patches, and stays credited.
  Cares about not being pinged into the ground.
- **Knowledge / operations lead** (KB admin, ops, enablement). Owns corpus health, decay defaults,
  ownership metadata, and channel-consent settings. Cares about staleness burn-down and coverage.
- **Security / compliance reviewer**. Needs deterministic ACL enforcement, as-of answers for
  disputes and audits, and evidence that nothing leaked. Cares about zero ACL leakage and an
  auditable memory.

## Jobs to be done

1. Answer a current question with a citation and a warranty label that states how much to trust it.
2. Answer *as-of* a date ("what did the refund policy say on February 14?") and *changed-since*
   ("what moved since the audit?").
3. Turn recurring failed and low-confidence queries into demand-ranked gap tickets routed to the
   right owner.
4. Capture a two-sentence owner reply (or a Slack thread that resolved what search missed) into a
   first-class, provenance-carrying KB entry — only after human approval.
5. Refuse to average two high-authority sources that materially conflict; surface both and open a
   ticket to reconcile.

## Novelty (scoped)

As of July 2026, the open and commercial internal-search tools we surveyed (including Glean, Onyx,
Dust, and the broader RAG-platform wave) treat the corpus as a read-only input: they compete on
connector count and retrieval quality, and leave corpus health to someone else. Across that field we
found no tool where the query stream maintains the corpus, answers carry evidence-backed warranty
labels with as-of history, and material conflicts between high-authority sources refuse to
self-resolve. That inversion is Mycelium's bet. This is a scoped claim about the field we reviewed in
July 2026, not a claim of universal priority.

## Non-goals

- **Not a wiki editor or CMS.** Mycelium maintains the corpus through the query stream and approval
  gates; it does not replace authoring tools.
- **No individual productivity surveillance.** It inventories team-visible signals over documents and
  threads, aggregate-first, consent-scoped per channel — never individual scoring.
- **The LLM does not decide or compute.** Answer synthesis and claim extraction are the only
  non-deterministic stages. Access control, temporal storage, trust-vector math, decay clocks,
  conflict triggers, owner routing, and telemetry scoring are all deterministic. Nothing enters the
  corpus, and no ping is sent, without a deterministic gate and a human sign-off.
- **No cloud lock-in.** Self-hostable is a requirement, with a local-model mode, not a later tier.
- **Not a connector arms race.** Breadth of sources is deferred to the healing loop's value, not the
  headline.

## Success metrics (targets, not yet measured)

Retrieval quality on a labeled query set — recall@k and citation precision — plus the metrics no
incumbent reports: **gap-closure time**, **staleness burn-down**, **warranty calibration** (are
owner-verified answers accepted measurably more than best-available ones?), **as-of answer
correctness** on a versioned synthetic corpus with known history, and **conflict-detection
precision** on planted contradictions. **ACL leakage target: zero, tested adversarially.** These are
the acceptance criteria the Phase-1 eval harness (`EVAL.md`) will enforce; today it raises
`NotImplementedError` on purpose.
