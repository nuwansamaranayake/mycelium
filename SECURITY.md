# Security — Mycelium

Open-source tools get deployed into companies by people who never read the code. Mycelium treats
that as a design input. Its baseline is the **OWASP Top 10 for LLM Applications (2025)** and the
**NIST AI Risk Management Framework — Generative AI Profile (NIST AI 600-1)**. Because Mycelium reads
an organization's most sensitive corpus and can route repair tasks to people, its trust boundaries
are drawn deliberately: ACLs are enforced deterministically before any chunk reaches model context,
channel indexing is opt-in per channel with visible notice, and a local-model mode exists for
knowledge that cannot leave the building.

## OWASP LLM Top 10 (2025) → Mycelium controls

| OWASP LLM ID | Risk | Mycelium control |
|---|---|---|
| **LLM01 — Prompt Injection** | Retrieved documents or Slack threads carry instructions that hijack the model. | Retrieved content and uploads are untrusted **data**, never instructions. System prompt and content travel in separate channels; red-team injection cases ship in the eval suite. |
| **LLM02 — Sensitive Information Disclosure** | An answer surfaces a chunk the asker may not see. | ACL filtering at **retrieval time**, before generation, preserved through citations and caches. Post-generation redaction is not treated as access control. Local-model mode keeps the corpus in-building. |
| **LLM05 — Improper Output Handling** | LLM output is trusted downstream as fact or command. | Synthesis is claim-shaped with mandatory citations; deterministic code attaches the warranty label and decides state. A drafted patch is a *proposal* gated behind human approval — never an auto-write. |
| **LLM06 — Excessive Agency** | The system acts (pings owners, writes the corpus) without a human. | Nothing enters the corpus and no owner is pinged without a deterministic gate plus human sign-off. Pings carry per-owner rate limits; the LLM proposes, humans and code dispose. |
| **LLM08 — Vector & Embedding Weaknesses** | Poisoned or cross-tenant embeddings leak or mislead. | ACL scope is applied to the vector filter, not bolted on after; ingestion is deterministic and provenance-anchored, so a poisoned span traces to its source version. |
| **LLM09 — Misinformation** | Confident blending of stale or contradictory sources. | Trust vector (authority × freshness × corroboration) plus per-type decay clocks; material conflicts return `NEEDS_RESOLUTION` with both claims, not an average. Bitemporal storage makes "as of when" answerable. |
| **LLM10 — Unbounded Consumption** | Runaway tokens, tool calls, or loop depth. | Hard budgets on tokens, tool calls, and loop depth; every LLM call is logged as a trace (model, prompt hash, cost, latency). A runaway agent is a security incident. |

## NIST AI RMF — Generative AI Profile

Mycelium maps its practices to the NIST GenAI Profile's functions. **Govern:** documented trust
boundaries, consent-scoped channels, no individual scoring. **Map:** the claim/evidence provenance
chain makes every answer traceable to its source spans and versions. **Measure:** the `EVAL.md`
harness (ACL leakage, conflict precision, warranty calibration) is the measurement surface, with
Seismograph probing drift continuously. **Manage:** `RISKS.md` carries tripwires and owners;
`FAILURES.md` records what broke and the gate that caught it.

## Secrets

No provider SDK is called directly; all model access goes through the groundwork gateway, which reads
`OPENROUTER_API_KEY` from the environment. Secrets live in `.env` (git-ignored); `.env.example` ships
with blank keys, and the synthetic demo runs with no keys at all. Never commit a populated `.env`,
and never place corpus content or personal data in URL parameters or logs.
