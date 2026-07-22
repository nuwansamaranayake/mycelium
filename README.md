# Mycelium

> **Status: scaffold (v0.1).** The engineering harness is built and verified: live smoke test,
> fail-loud guards, migration checks, CI. The architecture described below is the design being
> built; Phase 1 is in progress. [ROADMAP.md](ROADMAP.md) shows what exists today versus what
> is next.

**Internal knowledge-base search with self-healing bitemporal memory.**

Search that repairs the knowledge base and remembers what was true when. Every failed query is a
work order. Every answer carries a warranty label. Conflicting documents surface as disagreements
instead of blending into confident nonsense, and "what did the policy say in February?" is a
first-class query.

## What it is

Mycelium is a self-hostable internal answer engine whose corpus gets *healthier the more it is
used*. Most enterprise search we reviewed (July 2026) treats the corpus as a
read-only input: retrieval quality climbed, corpus quality did not, and that is where the failures
live. The engine confidently serves the 2023 expense policy, blends two contradictory docs into one
fluent paragraph, and misses the answer that lives only in a Slack thread. Mycelium closes that loop:
queries reveal gaps, gaps become routed micro-tasks for the humans who know, their approved replies
patch the corpus with provenance, every served answer shows how much to trust it and why, and the
whole memory is queryable as of any date. Because the knowledge base is the one dataset most
companies will never ship to a vendor, it runs on your own hardware, with a local-model mode for
knowledge that cannot leave the building.

## How it works (the design)

A query is classified by intent (current, as-of, or changed-since), then answered by hybrid
retrieval (BM25 + vectors + a temporal filter), ACL-filtered deterministically before any chunk
reaches a model. Deterministic trust scoring combines source authority, freshness against a
per-type decay clock, and corroboration, and checks for conflict. An LLM synthesizes the answer with
mandatory citations; deterministic code attaches the warranty label and the valid period. Low
confidence spawns a **gap ticket**; a material conflict between high-authority sources returns a
`NEEDS_RESOLUTION` state showing both claims rather than averaging them. Gap tickets route to the
inferred document owner as a one-question micro-request; the owner's approved reply becomes a
first-class, bitemporal KB entry. Corrections never overwrite: the old record closes and a new one
opens, so "what did the refund policy say on February 14?" is answerable.

## What exists today (verified)

This scaffold's doctrine is already enforced, not promised. Three checks you can run in five minutes:

1. `python scripts/smoke_test.py` against a running instance: hits real endpoints and asserts
   non-empty, schema-valid data. Passes.
2. Set `APP_ENV=production` and call `/api/v1/demo`: returns 503, because fixture data outside
   development is forbidden by code, not by convention.
3. `python scripts/eval.py`: raises loudly instead of passing vacuously. An eval that cannot
   fail is theater; the real harness lands in Phase 1.

## The unique bet

The category competes on connector count and retrieval quality over a corpus it treats as someone
else's problem (the tools we reviewed as of July 2026). No open internal search we reviewed (July 2026) lets the query stream maintain the corpus, attaches evidence-backed warranty labels with as-of history, and refuses to self-resolve material conflicts. That inversion is the bet.

The full scoped novelty statement, with the field surveyed, is in [PRD.md](PRD.md).

The LLM is a sensor that turns messy documents into typed, span-anchored claims; deterministic code
enforces access, does the trust math, decides when to refuse, and routes the repair. Staleness you can
see is staleness you can fix.

## Quickstart (local, zero external keys)

### Standalone clone

```bash
python -m venv .venv
source .venv/bin/activate         # POSIX     (.venv\Scripts\activate on Windows)
pip install -e .[dev]             # groundwork resolves from GitHub automatically
cp .env.example .env              # POSIX     (copy .env.example .env on Windows)
uvicorn app.main:app --reload
```

### Developing the whole portfolio (sibling checkout, editable)

```bash
git clone https://github.com/nuwansamaranayake/groundwork ../groundwork
pip install -e ../groundwork
pip install -e .[dev]
```

Then, in another shell:

```bash
export API_PORT=8000 SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py   # POSIX -> SMOKE OK
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py  # Windows
```

The `/api/v1/demo` endpoint serves the synthetic dataset in `data/synthetic/`: no OpenRouter key, Postgres, or Redis is needed to see the app respond. Those are required only for Phase 1 features (real extraction, persistence, migrations).

## Demo

A screenshot and GIF of the three-question demo, "what is our refund window?" asked as of today, as
of last February, and for a region where two documents disagree, land with the Next.js frontend in
Phase 2. Until then, the synthetic fixture above shows the shape of a served answer, its warranty
label, and a `NEEDS_RESOLUTION` conflict.

## Doctrine

The non-negotiable engineering rules this repo is run by, fail loud, smoke-test real endpoints, no
silent fallbacks, live in [`DOCTRINE.md`](./DOCTRINE.md).
