"use client";
/* The demo: switch principals, ask, and watch the filter run before scoring.

   D1 is the product: the restricted principal's answer excludes the restricted document
   from results AND sources, with the exclusion counted from the same set retrieval
   filtered on. Honest states everywhere: zero passages says so, ungrounded sentences are
   flagged, unknown says unknown. */
import { useState } from "react";

import { api, friendly, useDemoSession } from "../../lib/session";

type Principal = { role: string; name: string; display: string; token: string };
type Session = {
  token: string; expires_in: number; request_budget: number; synthetic: boolean;
  principals: Principal[];
  documents: { document_id: number; title: string; restricted_to_broad: boolean }[];
  suggested_questions: { q: string; shows: string }[];
};
type Result = {
  passage_id: number; document_id: number; title: string; text: string;
  rank: number; fused_score: number;
  freshness: { label: string; age_days: number };
};
type QueryOut = {
  query_id: number; as_of: string; results: Result[];
  acl: { principal: string; visible_documents: number; excluded_documents: number;
         filtered_before_scoring: boolean };
};
type Sentence = { text: string; grounded: boolean; passage_ids: string[] };
type AnswerOut = { answer_id: number; text: string; ungrounded_count: number;
                   model: string; sentences: Sentence[] };

const S_KEY = "myc-demo-session";

function stripPrefix(title: string): string {
  return title.replace(/^demo-\d{8}T\d{6}Z-[0-9a-f]{6}-/, "");
}

export default function Demo() {
  const { session, start, drop, err, busy } = useDemoSession<Session>(S_KEY);
  return (
    <>
      <p className="dim mono small"><a href="/">Mycelium</a> / live demo</p>
      <h1>The demo</h1>
      <div className="panel limits">
        <strong>Synthetic corpus.</strong> Four seeded documents and two principals,
        labelled as such. One document is restricted to the broad principal; one is
        deliberately stale; two disagree about deploys. Anything you add lives in a
        session-scoped tenant and is deleted by the retention sweep once it is older than
        7 days.
      </div>
      {!session ? (
        <div className="panel">
          <button onClick={start} disabled={busy}>
            {busy ? "Opening session…" : "Start the demo — no sign-up"}
          </button>
          <p className="dim small">
            You get two real principals with their own bearer tokens, held only by this
            tab. Switching principals switches which token is sent — the access check runs
            on the same authentication path production uses. Every server read still
            requires a token.
          </p>
          {err && <p className="err">{err}</p>}
        </div>
      ) : (
        <SessionView session={session} restart={drop} />
      )}
    </>
  );
}

function SessionView({ session, restart }: { session: Session; restart: () => void }) {
  const [active, setActive] = useState("broad");
  const [fatal, setFatal] = useState("");
  const principal = session.principals.find((p) => p.role === active)!;
  const guard = (e: unknown) => {
    const msg = friendly(e);
    if (msg.startsWith("This ")) setFatal(msg);
    return msg;
  };
  if (fatal) {
    return (
      <div className="panel reject">
        <p>{fatal}</p>
        <button onClick={restart}>Start a new session</button>
      </div>
    );
  }
  return (
    <>
      <h2>1 · Who is asking? <span className="chip syn">synthetic</span></h2>
      <p>
        {session.principals.map((p) => (
          <button key={p.role} className={p.role === active ? undefined : "secondary"}
            style={{ marginRight: "0.6rem" }} onClick={() => setActive(p.role)}>
            {p.display}
          </button>
        ))}
        <span className="dim small">
          the switch changes which bearer token this tab sends — nothing else
        </span>
      </p>
      <p className="dim small">
        Corpus: {session.documents.map((d) => stripPrefix(d.title)).join(" · ")}.
        The runbook is readable only by Broad access.
      </p>
      <AskPanel key={principal.role} session={session} principal={principal} guard={guard} />
    </>
  );
}

function AskPanel({ session, principal, guard }: {
  session: Session; principal: Principal; guard: (e: unknown) => string;
}) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState<QueryOut | null>(null);
  const [msg, setMsg] = useState("");

  const ask = async (question: string) => {
    setBusy(true); setMsg(""); setOut(null); setQ(question);
    try {
      const d = await api<QueryOut>(principal.token, "/api/v1/query", {
        method: "POST",
        body: JSON.stringify({ principal: principal.name, query: question }),
      });
      setOut(d);
    } catch (e) { setMsg(guard(e)); }
    finally { setBusy(false); }
  };

  return (
    <>
      <h2>2 · Ask as {principal.display}</h2>
      <p>
        {session.suggested_questions.map((s) => (
          <button key={s.q} className="secondary" title={s.shows}
            style={{ margin: "0 0.5rem 0.5rem 0" }} onClick={() => ask(s.q)}>
            {s.q}
          </button>
        ))}
      </p>
      <p>
        <input type="text" value={q} placeholder="…or type your own question"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && q.trim()) ask(q.trim()); }} />
      </p>
      {busy && <p className="dim">Retrieving…</p>}
      {msg && <p className="err">{msg}</p>}
      {out && <ResultsView out={out} principal={principal} guard={guard} />}
    </>
  );
}

function ResultsView({ out, principal, guard }: {
  out: QueryOut; principal: Principal; guard: (e: unknown) => string;
}) {
  const excluded = out.acl.excluded_documents;
  return (
    <>
      <div className={`panel ${excluded > 0 ? "reject" : "pass"}`}>
        <p style={{ margin: 0 }}>
          <strong>Access filter, before scoring:</strong>{" "}
          {out.acl.visible_documents} document{out.acl.visible_documents === 1 ? "" : "s"}{" "}
          visible to this principal, <strong>{excluded} excluded</strong>.
          {excluded > 0 && <> The excluded document{excluded === 1 ? " was" : "s were"} never
          scored, never retrieved, never shown — the filter ran before ranking, not after
          generation.</>}
        </p>
      </div>

      {out.results.length === 0 ? (
        <div className="panel">
          <p style={{ margin: 0 }}>
            <strong>The corpus cannot answer this.</strong> Zero passages retrieved, so
            there is nothing to cite and no answer is synthesized. An honest miss, not a
            fluent guess.
          </p>
        </div>
      ) : (
        <>
          {out.results.map((r) => (
            <div className="bullet" key={r.passage_id}>
              <p style={{ margin: 0 }}>
                <strong>{stripPrefix(r.title)}</strong>
                <span className={`chip ${r.freshness.label === "fresh" ? "ok"
                  : r.freshness.label === "stale" ? "bad" : ""}`}>
                  {r.freshness.label} · {r.freshness.age_days}d
                </span>
                <span className="chip">rank {r.rank}</span>
              </p>
              <p className="small dim" style={{ margin: "0.3rem 0 0" }}>{r.text}</p>
            </div>
          ))}
          <p className="dim small">
            Freshness is date arithmetic against each document&apos;s timestamp, attached
            by deterministic code — the model never labels anything. Computed at{" "}
            {new Date(out.as_of).toUTCString()}.
          </p>
          <AnswerPanel out={out} principal={principal} guard={guard} />
        </>
      )}
    </>
  );
}

function AnswerPanel({ out, principal, guard }: {
  out: QueryOut; principal: Principal; guard: (e: unknown) => string;
}) {
  const [busy, setBusy] = useState(false);
  const [ans, setAns] = useState<AnswerOut | null>(null);
  const [msg, setMsg] = useState("");
  const [openCite, setOpenCite] = useState<string | null>(null);
  const byId = new Map(out.results.map((r) => [String(r.passage_id), r]));

  const synthesize = async () => {
    setBusy(true); setMsg("");
    try {
      const d = await api<AnswerOut>(principal.token, "/api/v1/answers", {
        method: "POST", body: JSON.stringify({ query_id: out.query_id }),
      });
      setAns(d);
    } catch (e) { setMsg(guard(e)); }
    finally { setBusy(false); }
  };

  if (!ans)
    return (
      <p>
        <button onClick={synthesize} disabled={busy}>
          {busy ? "Synthesizing…" : "Synthesize the cited answer"}
        </button>{" "}
        <span className="dim small">the model phrases from the passages above; every
        sentence cites or is flagged</span>
        {msg && <span className="err small"> {msg}</span>}
      </p>
    );

  return (
    <div className="panel">
      <h2 style={{ marginTop: 0 }}>3 · The answer, sentence by sentence</h2>
      {ans.sentences.map((s, i) => (
        <p key={i} style={{ margin: "0.4rem 0" }}>
          {s.text}{" "}
          {s.grounded ? (
            s.passage_ids.map((pid) => (
              <button key={pid} className="secondary chip" style={{ cursor: "pointer" }}
                onClick={() => setOpenCite(openCite === `${i}-${pid}` ? null : `${i}-${pid}`)}>
                cite:{pid}
              </button>
            ))
          ) : (
            <span className="chip bad">ungrounded — flagged, not hidden</span>
          )}
          {s.passage_ids.map((pid) => openCite === `${i}-${pid}` && byId.get(pid) && (
            <span key={`o${pid}`} className="panel small" style={{ display: "block", margin: "0.4rem 0" }}>
              <strong>{stripPrefix(byId.get(pid)!.title)}</strong>{" "}
              <span className={`chip ${byId.get(pid)!.freshness.label === "fresh" ? "ok" : "bad"}`}>
                {byId.get(pid)!.freshness.label}
              </span>
              <br />{byId.get(pid)!.text}
            </span>
          ))}
        </p>
      ))}
      <p className="dim small" style={{ marginBottom: 0 }}>
        {ans.ungrounded_count === 0
          ? "Every sentence grounded in a cited passage."
          : `${ans.ungrounded_count} sentence(s) the model could not ground — flagged above.`}{" "}
        Model: <code>{ans.model}</code>.
      </p>
    </div>
  );
}
