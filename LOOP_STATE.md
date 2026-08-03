# LOOP_STATE — Mycelium, Ship to Demo, plus the Shared Demo Kit

Run started 2026-08-03. Order fixed: A, B, C, D1, rest of D, G, H; E if time; F stretch.
Resume: read this file top to bottom, continue at the first `todo`.
(Phase 1's milestone record lives in this file's git history, closed GATES_PASSED.)

## The objective

A stranger opens https://mycelium.aigniteconsulting.ai, uses it with no credentials, and
**watches the knowledge base refuse to leak a restricted document** — filter before
retrieval scoring, visible in the UI. Cited answers, warranty labels, honest misses.

## Environment facts (audited 2026-08-03, do not re-derive)

- mycelium deployed at SHA `745f025`, tags to v0.2.3, serves `version: 0.1.0` (the Part A
  defect). Served routes: POST /api/v1/{answers,documents,ingest/folder,principals,query},
  GET /api/v1/answers/{aid}, GET /api/v1/demo, GET /health. 9 tables.
- groundwork at v0.1.1 (`fc34b3a`), package dir `groundwork/groundwork/`, modules: claims,
  config (BaseConfig), gateway, trace, verification. Apps pin via git URL @v0.1.1.
- mycelium engine modules: chunking, corpus, embedding, freshness, retrieval, synthesis —
  warranty/freshness logic already exists server-side.
- CareerCompiler demo kit to extract: `careercompiler/app/demo.py` (sessions/budget/TTL/
  prefix) + `_auth`/`_guard` in routes.py + FakeRedis in tests/test_demo.py + web shell
  (globals.css, layout.tsx, useSession/api/friendly in demo/page.tsx).
- Estate retention ALREADY sweeps `demo-` prefixes for any app whose ROOTS carry them;
  mycelium ROOTS = documents.title + principals.name (portfolio-ops retention.py). C5 needs
  only prefix discipline + a row-count drill.
- Host: beacon-gom, snapshot before first deploy (Hostinger VM id 1033016; snapshots last
  24h). careercompiler container runs NLI at 1500m cap — **F1: never a second torch
  container.**

## Design decisions taken (DECISION log)

- A1: `groundwork.web.build_version()` (reads APP_VERSION, default "unreleased") +
  `groundwork.testing.assert_served_version_matches_front_page(client)`; apps pass
  `version=build_version()` to FastAPI and front pages read the same helper. Pin bump
  v0.1.1 -> v0.2.0 in all six apps.
- B1: `groundwork.demokit.DemoKit` — redis-backed sessions, tenant prefix
  `demo-<stamp>Z-<hex>-`, TTL/budget/ip-limit as constructor params fed from BaseConfig
  fields; `guard_prefix()` helper; FakeRedis moves to `groundwork.testing`. Retention stays
  in portfolio-ops (no second implementation).
- B5: web shell extracted to `groundwork/webshell/` (css, layout, session hook, api client)
  as source of truth; mycelium consumes a copy (Docker build context cannot reach a sibling
  repo, so vendor-by-copy with a provenance header). CC's pages adopt the shell in a
  follow-up pass, not the night before its demo — recorded in BLOCKED.md.
- D1 leak-proof rendering: the restricted-principal answer shows "N candidate passages
  excluded by ACL before scoring", sourced from the retrieval trace, so the filter's
  position is visible, not asserted.

## Progress

| Part | Status | Evidence |
|---|---|---|
| Audit | done | this file, header |
| A1/A3 groundwork helper + shared assertion | **done** | groundwork `2ae0847`, 22 tests |
| A2 careercompiler on the helper | **done** | CC `2f0452b`, 78 tests on groundwork v0.2.0 |
| A2 remaining four apps | **done** | Seismograph `400667d`, Triage `ae74973`, Almanac `82508d6`, Parallax `f87d338`; all suites green on v0.2.0 (45/54/58/37) |
| B1/B3 demokit extracted + proven | **done** | groundwork `2ae0847`; 6 kit tests (403/429/expiry/rate/prefix shape) |
| B4 CC refactor onto the kit | **done** | CC `2f0452b`; suite passed unchanged, which is B4's proof |
| B5 webshell extracted | **done** | groundwork/webshell/ (css, layout, lib/session.ts) |
| C demo access + seed | **done** | `586dd20` + answers-auth commit; 40 tests incl. the ACL refusal with positive anchor |
| D1–D4, D6 frontend | **done** | web/ committed; local E2E 2x 10/10 (`evidence/2026-08-03-local-e2e.txt`); wildcard-ACL tenancy hole found by E2E and closed |
| D5 upload + D7 contracts | **done** | `de51cd6`; literal enforcement green |
| D8 truth layer | **done** | docs/agent-legibility doc; copy written from it; novelty claim survey-scoped on the page |
| G | **done** | estate gate exit 0 incl. mycelium production negatives; TLS verify 0; walkthrough `evidence/2026-08-03-production-walkthrough.txt` |
| H | **done** | all 7 repos pushed, CI green observed per repo BEFORE tags (groundwork v0.2.0, CC v0.3.2, mycelium v0.3.0, ops v0.4.0, four apps v0.3.2); snapshot 02:32Z; deployed: mycelium + the four slim apps; estate gate exit 0 after |
| E healing loop | **not built, stated honestly** | ROADMAP says Phase 2 partial and names it |
| F conflict detection | not built | F1 held: zero new torch containers |

## BLOCKED
(none yet)

## Next action on resume

1. DONE (CC `2f0452b`). Was: A2+B4 in careercompiler: pyproject pin `aignite-groundwork @ git+...@v0.2.0` (tag does
   not exist yet — push groundwork + tag first, or pin the SHA `2ae0847` until the tag);
   replace app/demo.py's session/prefix code with `from groundwork import DemoKit,
   DemoRefused, guard_prefix`; `_auth` catches DemoRefused -> HTTPException; delete the
   duplicated FakeRedis from tests (import from groundwork.testing); main.py/frontpage
   import groundwork.build_version. Suite must pass unchanged (B4's proof).
2. DONE — all four committed, suites green.
3. NOW: Part C — mycelium demo access via the kit. Read mycelium app/routes.py (auth
   pattern mirrors CC pre-refactor: _auth against SMOKE_TEST_TOKEN), wire DemoKit exactly
   as CC's 2f0452b does (demo.py wrapper + _auth DemoRefused mapping + guard on
   documents.title / principals.name prefixes), add POST /api/v1/demo/session seeding:
   principals demo-<p>broad + demo-<p>restricted; 4 docs (restricted: acl only broad;
   stale: old observed_at so freshness labels stale; fresh: answers 'what is the deploy
   process'; two conflicting on the same question), all titles demo-prefixed. Query flow
   needs principal param already served. Then D1 (web app vendoring groundwork/webshell),
   D, G, H. Apps NOT yet pushed: the four A2 apps + CC B4 + mycelium — push at H, CI green
   before tags, deploy wave with snapshot first. H order: groundwork push+tag v0.2.0 FIRST (CI green before tag).

## Groundwork: pushed and tagged
- v0.2.0 = `2ae0847`, CI green (3 checks) observed BEFORE the tag. Apps pin @v0.2.0.
- CC is NOT yet pushed/deployed with the refactor: its next push must wait for a CI run
  (the pin resolves from GitHub, so CI will exercise groundwork v0.2.0 for real), then
  deploy rides mycelium's H wave.

## Part C wiring facts (read from routes.py, do not re-read)

- `_store_document(s, external_id=, title=, text=, source=, doc_timestamp=,
  allowed_principals=) -> (did, n_chunks)` chunks + writes acl_entries.
- Principals carry their OWN bearer tokens (`principals.token`, issued at registration);
  `/query` authenticates via `_bind_principal` (token must match claimed principal).
  So the demo session returns BOTH seeded principals' tokens and the UI's principal
  switcher just switches which bearer it sends — the ACL demo rides existing auth.
- `_auth` is the admin gate on mutations. Demo upload (D5) needs a scoped path: demo
  session token allows document upload with title forced to the tenant prefix and
  allowed_principals restricted to tenant-prefixed principals.
- Query budget for demo principals: redis INCR `demo:q:{principal}` TTL = session TTL,
  cap = demo_request_budget, refuse 429 (synthesis costs LLM tokens).
- Seed: principals {prefix}broad, {prefix}restricted. Docs (titles prefixed):
  R "Incident Response Runbook (restricted)" acl [broad] with fact "failover vault
  rotated every 30 days"; S "Deploy Process (2023)" doc_timestamp 2023 (stale) says
  Jenkins; F "Deploy Process (current)" fresh, says GitHub Actions + smoke gate (S/F =
  the material disagreement pair); N "Onboarding FAQ" fresh, VPN answer. Honest-miss
  question: parental leave policy (no doc). D1 needs the /query response to carry an
  `excluded_by_acl` count sourced from the retrieval trace — check /query body + engine
  filter position when wiring.

## D-wave facts (shapes verified, do not re-read)

- /query response: {query_id, as_of, results:[{passage_id, document_id, title, text, span,
  rank, bm25/cosine/fused scores, freshness:{label, age_days}}], acl:{principal,
  visible_documents, excluded_documents, filtered_before_scoring}}. Off-corpus questions
  return results=[] (measured: parental leave + nonsense -> []; vpn/deploys -> 0.033) —
  the honest miss is deterministic at retrieval; the UI gates on empty results and never
  calls /answers (which also 422s on empty retrievals as backstop).
- /answers POST {query_id} with the QUERY OWNER's principal token -> {answer_id, text,
  ungrounded_count, model, sentences:[{text, grounded, passage_ids}]}. Show ungrounded
  sentences flagged; citations resolve to passages already held from /query results.
- Mycelium EVAL limits block (verbatim for the landing, gate asserts): "On a golden corpus
  of synthetic documents with planted timestamps and access rules, retrieval leaks nothing
  across principal boundaries (0 ACL leaks), every citation resolves to text that exists
  in the cited passage (1.0), every freshness label matches the planted timestamp (1.0),
  and the retrieved document set is stable across query paraphrases (jaccard 1.0 against a
  0.60 bound); the corpus is synthetic, so it does not measure recall on a real knowledge
  base."
- Web app: mirror CC's proven structure exactly (package.json/tsconfig/next.config with
  output:'export'; app/globals.css + layout from groundwork/webshell with provenance
  header; lib from webshell/lib/session.ts). Pages: landing (hero: the ACL refusal story,
  limits verbatim, "not for" and D8 novelty claim scoped to the July 2026 survey) and
  /demo (principal switcher = which bearer is sent; suggested-question chips; ACL banner
  from acl.excluded_documents; freshness chips with age_days + "label attached by
  deterministic code"; honest-miss panel on results=[]; synthesize button -> sentences
  with [n] citations, ungrounded flagged; citation click -> passage panel; upload D5 can
  reuse /documents with demo scope — NOT yet wired for demo tokens, add or defer with a
  BLOCKED line). main.py serving + Dockerfile web stage: copy CC's (no torch here — image
  stays slim). Then contracts.md re-derive + CC-style literal test port, truth-layer doc
  to docs/agent-legibility/ BEFORE copy lands, local compose E2E, G smoke extension
  (mycelium loop + demo cross-tenant 403 + no-token 401s + restricted-doc negative), H
  wave (push all repos, CI green -> tags: groundwork done; CC v0.3.2; mycelium v0.3.0;
  portfolio-ops minor; snapshot; deploy mycelium (+CC rebuild for B4? CC deploy optional
  — code-only refactor, same behavior; decide at H), estate smoke, walkthrough, 1h stats).

## Post-wave notes (2026-08-03)

- DECISION: careercompiler's B4 refactor is tagged v0.3.2 with CI green but NOT redeployed
  — its live v0.3.1 is demo-critical tomorrow and B4 is behavior-identical by its own
  proof. Redeploy rides the next CC wave.
- Triage incident during the A2 wave: service-netns recreate trap, ~minutes of 502, fixed
  by full-stack recreate; recorded in Triage/FAILURES.md. Estate gate exit 0 afterwards.
- H5 stats watch running on the host (pid 3963180, /tmp/myc-stats-watch.log).
- Served versions verified live: seismograph/triage/almanac/parallax 0.3.2, mycelium
  0.3.0, careercompiler 0.3.1 — the estate version defect is closed end to end.
