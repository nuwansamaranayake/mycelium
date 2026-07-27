"""Key-gated LLM eval: the real answer-synthesis stage, measured — never a required CI
check, never a silent skip.

Two measures, bounds stated here before the first run:
  citation coverage    = 1.00   every generated sentence cites at least one passage id
  grounding validity   = 1.00   every cited passage id is one of the retrieved passages

Retrieval feeding the model is the deterministic keyless pipeline (HashingEmbedder, golden
corpus, ACL-filtered); what this measures is the LLM stage behind it, through the real
groundwork gateway. The retrieval-stability invariant these queries exercise is declared in
contracts/retrieval-stability.yaml. Writes eval_report_llm.md. Exits nonzero on a miss
(when it runs at all).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groundwork import BaseConfig, LLMGateway  # noqa: E402
from app.engine.corpus import build_corpus  # noqa: E402
from app.engine.embedding import HashingEmbedder  # noqa: E402
from app.engine.freshness import freshness  # noqa: E402
from app.engine.retrieval import retrieve  # noqa: E402
from app.engine.synthesis import synthesize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "data" / "synthetic" / "golden" / "golden.json"
REPORT = ROOT / "eval_report_llm.md"

QUERY_IDS = ["q-refund-alice", "q-expense-alice", "q-holiday-alice"]
COVERAGE_BOUND = 1.00
VALIDITY_BOUND = 1.00


def main() -> None:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("LLM_MODEL_REASONING", "")
    if not key or not model:
        print("eval_llm: NOT RUN — OPENROUTER_API_KEY / LLM_MODEL_REASONING missing. "
              "This section is key-gated by design; the deterministic suite in "
              "scripts/eval.py is the required gate.", file=sys.stderr)
        sys.exit(2)

    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    ref = datetime.fromisoformat(data["reference_time"])
    passages, acls, timestamps = build_corpus(data["documents"])
    by_id = {p.passage_id: p for p in passages}
    queries = {q["query_id"]: q for q in data["queries"]}
    gw = LLMGateway(BaseConfig(openrouter_api_key=key))
    embedder = HashingEmbedder()

    sent_total = sent_cited = 0
    ids_total = ids_valid = 0
    rows_out: list[str] = []

    for qid in QUERY_IDS:
        q = queries[qid]
        hits = retrieve(q["query"], passages, q["principal"], acls, embedder, 3)
        ctx = [{"passage_id": h.passage_id, "text": by_id[h.passage_id].text,
                "freshness_label": freshness(timestamps[h.doc_id], ref).label}
               for h in hits]
        answer = synthesize(gw, model, q["query"], ctx)
        valid_ids = {h.passage_id for h in hits}
        for s in answer.sentences:
            sent_total += 1
            sent_cited += int(bool(s.passage_ids))
            for pid in s.passage_ids:
                ids_total += 1
                ids_valid += int(pid in valid_ids)
        rows_out.append(f"{qid}: sentences={len(answer.sentences)} "
                        f"ungrounded={answer.ungrounded_count} "
                        f"answer={answer.text[:100]!r}")

    coverage = sent_cited / sent_total if sent_total else 0.0
    validity = ids_valid / ids_total if ids_total else 0.0

    rows = [
        "# Mycelium key-gated synthesis eval",
        "",
        f"model: {model}",
        "",
        *rows_out,
        "",
        "| metric | value | bound | pass |",
        "|---|---|---|---|",
        f"| citation coverage | {coverage:.2f} | >= {COVERAGE_BOUND} | "
        f"{'PASS' if coverage >= COVERAGE_BOUND else 'FAIL'} |",
        f"| grounding validity | {validity:.2f} | >= {VALIDITY_BOUND} | "
        f"{'PASS' if validity >= VALIDITY_BOUND else 'FAIL'} |",
        "",
        "contract: contracts/retrieval-stability.yaml (keyless invariant measured by "
        "scripts/eval.py; this section measures the synthesis stage)",
    ]
    text = "\n".join(rows) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if coverage < COVERAGE_BOUND or validity < VALIDITY_BOUND:
        print("EVAL_LLM FAILED", file=sys.stderr)
        sys.exit(1)
    print("EVAL_LLM OK")


if __name__ == "__main__":
    main()
