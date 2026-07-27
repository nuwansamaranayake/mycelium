"""CLI retrieval: keyless, serverless, honest.

Usage:
    python -m app.cli query --corpus data/synthetic/golden/golden.json \
                            --principal alice --query "What is our refund window?" [--top-k 3]

Loads a golden-format corpus, runs the deterministic ACL-filtered hybrid retrieval, and
prints each hit with its citation (doc id + span) and freshness label computed against the
corpus reference_time. Exits nonzero when nothing clears the relevance floor, so a script
can branch on an honest empty set.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .engine.corpus import build_corpus
from .engine.embedding import HashingEmbedder
from .engine.freshness import freshness
from .engine.retrieval import retrieve


def query(corpus_path: str, principal: str, text: str, top_k: int) -> int:
    data = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
    ref = datetime.fromisoformat(data["reference_time"])
    passages, acls, timestamps = build_corpus(data["documents"])
    hits = retrieve(text, passages, principal, acls, HashingEmbedder(), top_k)
    if not hits:
        print("no passage cleared the relevance floor for this principal and query",
              file=sys.stderr)
        return 1
    by_id = {p.passage_id: p for p in passages}
    for h in hits:
        p = by_id[h.passage_id]
        fl = freshness(timestamps[h.doc_id], ref)
        print(f"#{h.rank} {h.passage_id} [{fl.label}, {fl.age_days}d] "
              f"span=({p.span_start},{p.span_end}) fused={h.fused_score}")
        print(f"   {p.text}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="mycelium")
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query", help="ACL-filtered hybrid retrieval over a golden-format corpus")
    q.add_argument("--corpus", required=True)
    q.add_argument("--principal", required=True)
    q.add_argument("--query", required=True)
    q.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()
    sys.exit(query(args.corpus, args.principal, args.query, args.top_k))


if __name__ == "__main__":
    main()
