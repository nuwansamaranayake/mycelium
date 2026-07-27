"""Eval harness: the golden retrieval suite against the EVAL.md Phase 1 thresholds.

Deterministic and keyless (HashingEmbedder, golden synthetic corpus with planted timestamps
and ACLs, labeled queries with pre-authored paraphrases, planted restricted-principal
cases). Staleness math uses the corpus reference_time, never wall-clock now. Writes
eval_report.md so consecutive runs can be compared byte-for-byte. The key-gated synthesis
section (real gateway) is reported separately by scripts/eval_llm.py and is never a required
check — and never a silent skip: this harness says loudly whether it ran.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.corpus import build_corpus  # noqa: E402
from app.engine.embedding import HashingEmbedder  # noqa: E402
from app.engine.freshness import freshness  # noqa: E402
from app.engine.retrieval import retrieve  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "data" / "synthetic" / "golden" / "golden.json"
REPORT = ROOT / "eval_report.md"

BOUNDS = {
    "retrieval_hit_at_3": 0.85,
    "acl_leak_count": 0,
    "citation_validity": 1.00,
    "freshness_correctness": 1.00,
    "retrieval_stability_min": 0.60,
}
TOP_K = 3
LEAK_PROBE_K = 10  # leak checks retrieve deeper than the UI would show, on purpose


def _jaccard(a: set, b: set) -> float:
    union = a | b
    return (len(a & b) / len(union)) if union else 1.0


def main() -> None:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    ref = datetime.fromisoformat(data["reference_time"])
    passages, acls, timestamps = build_corpus(data["documents"])
    doc_texts = {d["doc_id"]: d["text"] for d in data["documents"]}
    by_id = {p.passage_id: p for p in passages}
    embedder = HashingEmbedder()

    hit_total = hit_ok = 0
    leak_count = 0
    citation_total = citation_ok = 0
    fresh_total = fresh_ok = 0
    stability_min = 1.0
    rows_out: list[str] = []

    def audit_citations(hits) -> None:
        nonlocal citation_total, citation_ok
        for h in hits:
            p = by_id[h.passage_id]
            citation_total += 1
            citation_ok += int(
                doc_texts[p.doc_id][p.span_start:p.span_end] == p.text)

    for q in data["queries"]:
        base = retrieve(q["query"], passages, q["principal"], acls, embedder, TOP_K)
        audit_citations(base)
        base_docs = {h.doc_id for h in base}

        if q["expected_doc_ids"]:
            hit_total += 1
            hit_ok += int(any(d in base_docs for d in q["expected_doc_ids"]))

        forbidden = set(q["forbidden_doc_ids"])
        for text in [q["query"], *q["paraphrases"]]:
            deep = retrieve(text, passages, q["principal"], acls, embedder, LEAK_PROBE_K)
            leak_count += sum(1 for h in deep if h.doc_id in forbidden)
            # global invariant, not just planted cases: every surfaced doc is visible
            for h in deep:
                assert q["principal"] in acls[h.doc_id] or "*" in acls[h.doc_id], \
                    f"ACL breach outside planted set: {h.doc_id} to {q['principal']}"

        if q["expected_doc_ids"]:
            for text in q["paraphrases"]:
                v = retrieve(text, passages, q["principal"], acls, embedder, TOP_K)
                audit_citations(v)
                stability_min = min(
                    stability_min, _jaccard(base_docs, {h.doc_id for h in v}))

        rows_out.append(
            f"{q['query_id']}: top{TOP_K}={sorted(base_docs)}"
            + (f" expected={q['expected_doc_ids']}" if q["expected_doc_ids"] else
               f" forbidden={q['forbidden_doc_ids']} (planted ACL case)"))

    for d in data["documents"]:
        fresh_total += 1
        fresh_ok += int(
            freshness(timestamps[d["doc_id"]], ref).label == d["expected_freshness"])

    metrics = {
        "retrieval_hit_at_3": hit_ok / hit_total,
        "acl_leak_count": leak_count,
        "citation_validity": citation_ok / citation_total,
        "freshness_correctness": fresh_ok / fresh_total,
        "retrieval_stability_min": stability_min,
    }
    passes = {
        "retrieval_hit_at_3": metrics["retrieval_hit_at_3"] >= BOUNDS["retrieval_hit_at_3"],
        "acl_leak_count": metrics["acl_leak_count"] <= BOUNDS["acl_leak_count"],
        "citation_validity": metrics["citation_validity"] >= BOUNDS["citation_validity"],
        "freshness_correctness":
            metrics["freshness_correctness"] >= BOUNDS["freshness_correctness"],
        "retrieval_stability_min":
            metrics["retrieval_stability_min"] >= BOUNDS["retrieval_stability_min"],
    }

    lines = ["# Mycelium golden retrieval eval report", "",
             f"reference_time: {data['reference_time']} (staleness anchor; "
             "no wall-clock in this path)", ""]
    lines += rows_out + ["", "| metric | value | bound | pass |", "|---|---|---|---|"]
    for k, v in metrics.items():
        op = "<=" if k == "acl_leak_count" else ">="
        val = round(v, 4) if isinstance(v, float) else v
        lines.append(f"| {k} | {val} | {op} {BOUNDS[k]} | {'PASS' if passes[k] else 'FAIL'} |")
    if os.environ.get("OPENROUTER_API_KEY"):
        lines += ["", "key-gated synthesis section: run scripts/eval_llm.py "
                      "(not part of this deterministic report)"]
    else:
        lines += ["", "key-gated synthesis section: NOT RUN (no OPENROUTER_API_KEY); "
                      "deterministic bounds above are the required gate"]
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if not all(passes.values()):
        print("EVAL FAILED: at least one threshold missed (see rows above)", file=sys.stderr)
        sys.exit(1)
    print("EVAL OK")


if __name__ == "__main__":
    main()
