/* Landing. Every sentence traces to docs/agent-legibility/2026-08-03-frontend-truth-layer.md;
   the limits block is verbatim from EVAL.md and the deploy gate asserts it stays that way. */
import Link from "next/link";

const LIMITS =
  "On a golden corpus of synthetic documents with planted timestamps and access rules, " +
  "retrieval leaks nothing across principal boundaries (0 ACL leaks), every citation " +
  "resolves to text that exists in the cited passage (1.0), every freshness label " +
  "matches the planted timestamp (1.0), and the retrieved document set is stable across " +
  "query paraphrases (jaccard 1.0 against a 0.60 bound); the corpus is synthetic, so it " +
  "does not measure recall on a real knowledge base.";

export default function Landing() {
  return (
    <>
      <p className="dim mono small">Mycelium · an AiGNITE portfolio build</p>
      <h1>RAG that shows you what it refused to read.</h1>
      <p>
        Internal knowledge-base search where access control runs{" "}
        <strong>before retrieval scoring</strong>, not after generation. Ask as a broad
        principal and get a cited answer; switch to a restricted principal, ask the same
        question, and the restricted document stays out of the answer, out of the sources
        — and the exclusion is counted on screen from the same filter retrieval used.
      </p>

      <div className="panel">
        <p style={{ margin: 0 }}>
          <Link href="/demo/">
            <button>Open the live demo</button>
          </Link>
          <span className="dim" style={{ marginLeft: "0.8rem" }}>
            No sign-up. Synthetic corpus, labelled as such. Sessions expire on their own.
          </span>
        </p>
      </div>

      <h2>What it actually does</h2>
      <p>
        <strong>Warranty labels, computed not opined.</strong> Every retrieved passage
        carries fresh, aging, or stale — date arithmetic against the document&apos;s
        timestamp, attached by deterministic code, never by the model.
      </p>
      <p>
        <strong>Citations that resolve.</strong> Every answer sentence cites the passages
        it drew from; sentences the model could not ground are counted and flagged, not
        hidden. Click a citation, land on the passage.
      </p>
      <p>
        <strong>Honest misses.</strong> A question the corpus cannot answer returns zero
        passages and says so. Synthesis is never called on an empty retrieval.
      </p>
      <p className="dim small">
        Of the tools we reviewed in a July 2026 survey, most enforce access rules after
        generation, if at all. The self-healing loop — gap tickets from failed queries,
        owner-approved patches — is the roadmap&apos;s next phase, not on this page.
      </p>

      <h2>Published limits</h2>
      <div className="panel limits">
        <p style={{ margin: 0 }}>{LIMITS}</p>
      </div>

      <p className="small dim" style={{ marginTop: "3rem" }}>
        <a href="/docs">API reference</a> ·{" "}
        <a href="https://github.com/nuwansamaranayake/mycelium">source</a> · the LLM
        senses, deterministic code decides, humans approve.
      </p>
    </>
  );
}
