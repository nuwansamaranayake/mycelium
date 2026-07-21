# Mycelium

**Internal knowledge-base search with self-healing bitemporal memory.**

Search that repairs the knowledge base and remembers what was true when. Every failed query is a
work order. Every answer carries a warranty label. Conflicting documents surface as disagreements
instead of blending into confident nonsense, and "what did the policy say in February?" is a
first-class query.

## What it is

Mycelium is a self-hostable internal answer engine whose corpus gets *healthier the more it is
used*. Most enterprise search (Glean, Onyx, Dust, the RAG platform wave) treats the corpus as a
read-only input: retrieval quality climbed, corpus quality did not, and that is where the failures
live — the engine confidently serves the 2023 expense policy, blends two contradictory docs into one
fluent paragraph, and misses the answer that lives only in a Slack thread. Mycelium closes that loop:
queries reveal gaps, gaps become routed micro-tasks for the humans who know, their approved replies
patch the corpus with provenance, every served answer shows how much to trust it and why, and the
whole memory is queryable as of any date. Because the knowledge base is the one dataset most
companies will never ship to a vendor, it runs on your own hardware, with a local-model mode for
knowledge that cannot leave the building.

## How it works

A query is classified by intent (current, as-of, or changed-since), then answered by hybrid
retrieval (BM25 + vectors + a temporal filter), ACL-filtered deterministically before any chunk
reaches a model. Deterministic trust scoring combines source authority, freshness against a
per-type decay clock, and corroboration, and checks for conflict. An LLM synthesizes the answer with
mandatory citations; deterministic code attaches the warranty label and the valid period. Low
confidence spawns a **gap ticket**; a material conflict between high-authority sources returns a
`NEEDS_RESOLUTION` state showing both claims rather than averaging them. Gap tickets route to the
inferred document owner as a one-question micro-request; the owner's approved reply becomes a
first-class, bitemporal KB entry. Corrections never overwrite — the old record closes and a new one
opens — so "what did the refund policy say on February 14?" is answerable.

## The unique bet

The category competes on connector count and retrieval quality over a corpus it treats as someone
else's problem. Mycelium's bet is the inversion: **the only open internal search where the query
stream maintains the corpus, answers carry evidence-backed warranty labels with as-of history,
material conflicts refuse to self-resolve, and the whole system runs on your own hardware.** The LLM
is a sensor that turns messy documents into typed, span-anchored claims; deterministic code enforces
access, does the trust math, decides when to refuse, and routes the repair. Staleness you can see is
staleness you can fix.

## Quickstart (local, zero external keys)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on POSIX)
pip install -e ../groundwork      # sibling shared library (uv users: uv sync)
pip install -e .[dev]
copy .env.example .env            # leave keys blank; the demo runs on synthetic data
uvicorn app.main:app --reload
```

In another shell:

```bash
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py   # -> SMOKE OK
```

The `/api/v1/demo` endpoint serves the synthetic dataset in `data/synthetic/` — no OpenRouter
key, Postgres, or Redis needed to see the app respond. Those are required only for Phase 1
features (real extraction, persistence, migrations).

## Demo

A screenshot and GIF of the three-question demo — "what is our refund window?" asked as of today, as
of last February, and for a region where two documents disagree — land with the Next.js frontend in
Phase 2. Until then, the synthetic fixture above shows the shape of a served answer, its warranty
label, and a `NEEDS_RESOLUTION` conflict.

## Doctrine

The non-negotiable engineering rules this repo is run by — fail loud, smoke-test real endpoints, no
silent fallbacks — live in [`DOCTRINE.md`](./DOCTRINE.md).
