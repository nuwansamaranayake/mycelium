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
| C mycelium demo access + seed (restricted/stale/fresh/conflicting docs, 2 principals) | todo | |
| D1 ACL refusal screen | todo | |
| D2–D8 | todo | |
| G smoke extension + production negative (restricted doc must not leak, live) | todo | |
| H release wave (groundwork -> CC -> mycelium -> portfolio-ops) | todo | |
| E healing loop | stretch | |
| F conflict detection | stretch; F1 constraint absolute | |

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
