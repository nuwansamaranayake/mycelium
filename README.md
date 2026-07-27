# Mycelium

> **Status: Phase 1 core loop released (v0.2.0).** Two keyless connectors (folder
> ingester and direct upload), hybrid BM25 plus embedding retrieval with rank fusion, ACLs
> enforced before scoring, citations with deterministic freshness labels, and a key-gated
> LLM answer-synthesis stage. The deterministic eval suite is a required CI check.
> [ROADMAP.md](ROADMAP.md) shows what exists today versus what is next.

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

The doctrine is enforced, not promised. Five checks you can run in five minutes:

1. `python scripts/eval.py`: the deterministic keyless eval over a golden corpus with planted
   timestamps and ACLs. Observed on this build: retrieval hit@3 1.0, ACL leak count 0,
   citation validity 1.0, freshness correctness 1.0, paraphrase stability 1.0, and the report
   is byte-reproducible across runs (`eval_report.md`).
2. `python scripts/smoke_test.py` against a running instance: registers principals, uploads a
   document, ingests the demo folder, queries as a permitted principal (cited, freshness-labeled
   results) and as a forbidden one (the ACL holds even for a verbatim-text probe). Passes.
3. `python -m app.cli query --corpus data/synthetic/golden/golden.json --principal alice
   --query "What is our refund window?"`: keyless, serverless retrieval with citations and
   freshness labels.
4. Set `APP_ENV=production` and call `/api/v1/demo`: returns 503, because fixture data outside
   development is forbidden by code, not by convention.
5. `POST /api/v1/answers` without `OPENROUTER_API_KEY`: returns a typed 503 naming the missing
   key. With a key, the synthesis eval observed citation coverage 1.00 and grounding validity
   1.00 (`eval_report_llm.md`).

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
export API_PORT=8000 SMOKE_TEST_TOKEN=dev-smoke-token && python scripts/smoke_test.py   # POSIX -> SMOKE OK
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev-smoke-token && python scripts/smoke_test.py  # Windows
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
