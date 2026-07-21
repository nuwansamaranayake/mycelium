# 2. The LLM senses; deterministic code decides and computes

Date: 2026-07-21

## Status

Accepted

## Context

Mycelium answers questions over a company's most sensitive corpus, and it acts: it enforces access,
routes repair tasks to people, and writes new records into institutional memory. If the language
model were allowed to make those decisions, every consequential output would inherit the model's
non-determinism — an ACL decision that varies by phrasing, a trust score no one can reproduce, a
corpus write with no gate. The portfolio thesis is the opposite: the LLM is a **sensor** that turns
messy reality into typed, provenance-carrying claims, and deterministic code verifies those claims,
makes every decision, and computes every number. This ADR pins where that line falls for Mycelium,
grounded in the chapter's "Deterministic vs Non-Deterministic" split.

## Decision

**What the LLM senses (non-deterministic, and nothing more):**

- **Claim extraction** from documents — span-anchored, so every extracted claim points back to the
  exact source text it came from.
- **Answer synthesis** — with citations forced; the model composes prose over retrieved chunks but
  may not introduce a fact without a citation.
- **Contradiction judgment beyond numeric checks** — NLI-assisted entailment for the fuzzy cases
  that exact comparison cannot settle.
- **Gap-ticket summarization** and **patch drafting** from owner replies and Slack threads.
- **Ownership inference suggestions** — proposed, never applied; a human confirms.

**What deterministic code decides and computes (never the LLM):**

- **ACL enforcement at query time, always** — before any chunk reaches model context.
- **Ingestion, chunking, and hybrid retrieval** (BM25 + vectors + temporal filter).
- **Bitemporal storage and as-of filtering** — corrections close-and-open, never overwrite.
- **Decay clocks, trust-vector math, and warranty labels** — reproducible numbers, not model output.
- **Conflict triggers and the `NEEDS_RESOLUTION` state** — the materiality decision to refuse.
- **Owner routing, the approval workflow, and telemetry scoring** of every query.

Every consequential output — a served answer, a routed ping, a corpus write — passes a deterministic
gate, and anything that acts passes a human approval gate. The LLM's structured output is treated as
untrusted data until a deterministic check accepts it.

## Consequences

- Answers are reproducible where it matters: the same corpus and identity yield the same access
  decision, the same trust score, and the same warranty label, regardless of how the model phrased
  the prose around them.
- The model can hallucinate a claim, but a span-anchor check and citation gate reject it before it is
  served or stored; such rejections are logged to `FAILURES.md`.
- More engineering lives in the deterministic layer (retrieval, temporal storage, routing) than in
  prompts — deliberately. The novelty budget is spent on the architecture, not the model call.
- Swapping or downgrading the model (including to a local model for private operation) changes answer
  wording, not any decision or number, because decisions and numbers never lived in the model.
