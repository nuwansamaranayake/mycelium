import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.engine.chunking import chunk_document
from app.engine.corpus import build_corpus
from app.engine.embedding import HashingEmbedder
from app.engine.freshness import freshness
from app.engine.retrieval import allowed_doc_ids, retrieve
from app.engine.synthesis import EmptySynthesisError, synthesize

GOLDEN = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "synthetic" / "golden" /
     "golden.json").read_text(encoding="utf-8"))
REF = datetime.fromisoformat(GOLDEN["reference_time"])


def _corpus():
    return build_corpus(GOLDEN["documents"])


def test_chunk_spans_are_exact_substrings():
    text = "First paragraph here.\n\nSecond one.\n\n\n  Third with padding.  \n"
    chunks = chunk_document(text)
    assert [c.ordinal for c in chunks] == [0, 1, 2]
    for c in chunks:
        assert text[c.span_start:c.span_end] == c.text


def test_freshness_thresholds():
    doc_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def at(days):
        as_of = datetime.fromtimestamp(doc_ts.timestamp() + days * 86400, tz=timezone.utc)
        return freshness(doc_ts, as_of)
    assert at(0).label == "fresh"
    assert at(29).label == "fresh"
    assert at(30).label == "aging"
    assert at(180).label == "aging"
    assert at(181).label == "stale"
    # a document dated after the reference clamps to age 0, never negative
    future = freshness(datetime(2026, 2, 1, tzinfo=timezone.utc),
                       datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert future.label == "fresh" and future.age_days == 0


def test_freshness_rejects_naive_datetimes():
    with pytest.raises(ValueError):
        freshness(datetime(2026, 1, 1), datetime(2026, 2, 1, tzinfo=timezone.utc))


def test_retrieval_finds_relevant_doc():
    passages, acls, _ = _corpus()
    hits = retrieve("What is our refund window?", passages, "alice", acls,
                    HashingEmbedder(), top_k=3)
    assert hits and hits[0].doc_id == "doc-refund-policy"


def test_retrieval_handles_non_latin_scripts():
    # ASCII-only tokenization used to zero every signal for Cyrillic content,
    # returning an empty result set with no error (silently unretrievable docs)
    passages, acls, _ = _corpus()
    hits = retrieve("Сколько дней в неделю можно работать удалённо?", passages,
                    "alice", acls, HashingEmbedder(), top_k=3)
    assert hits and hits[0].doc_id == "doc-remote-ru"


def test_retrieval_is_deterministic():
    passages, acls, _ = _corpus()
    a = retrieve("expense report receipts", passages, "alice", acls, HashingEmbedder())
    b = retrieve("expense report receipts", passages, "alice", acls, HashingEmbedder())
    assert [(h.passage_id, h.fused_score) for h in a] == \
           [(h.passage_id, h.fused_score) for h in b]


def test_acl_forbidden_doc_never_surfaces():
    passages, acls, _ = _corpus()
    # alice literally quotes the payroll document; ACL must still exclude it
    hits = retrieve("Payroll runs on the 25th of each month salary payment schedule",
                    passages, "alice", acls, HashingEmbedder(), top_k=10)
    assert all(h.doc_id != "doc-payroll-calendar" for h in hits)
    # the privileged principal does see it — the planted case is real, not vacuous
    priv = retrieve("When does payroll run each month?", passages, "harriet", acls,
                    HashingEmbedder(), top_k=3)
    assert any(h.doc_id == "doc-payroll-calendar" for h in priv)


def test_acl_default_is_deny_and_principal_required():
    passages, acls, _ = _corpus()
    assert "doc-payroll-calendar" not in allowed_doc_ids("nobody-special", acls)
    with pytest.raises(ValueError):
        allowed_doc_ids("", acls)


class StubGateway:
    """Typed stub: returns a canned schema-shaped payload. No network."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete(self, *, model, messages, json_schema=None, temperature=0.0):
        self.calls.append({"model": model, "schema": json_schema})
        return self.payload


def test_synthesis_marks_ungrounded_sentences():
    gw = StubGateway({"sentences": [
        {"text": "Refunds are allowed within 30 days.", "passage_ids": ["doc-refund-policy#p0"]},
        {"text": "This cites nothing.", "passage_ids": []},
        {"text": "This cites a ghost.", "passage_ids": ["doc-ghost#p9"]},
    ]})
    answer = synthesize(gw, "test-model", "refund window?", [
        {"passage_id": "doc-refund-policy#p0", "text": "Customers may request...",
         "freshness_label": "fresh"},
    ])
    assert [s.grounded for s in answer.sentences] == [True, False, False]
    assert answer.ungrounded_count == 2
    assert gw.calls[0]["schema"]["name"] == "grounded_answer"


def test_synthesis_refuses_without_model_or_passages():
    gw = StubGateway({"sentences": []})
    with pytest.raises(RuntimeError):
        synthesize(gw, "", "q", [{"passage_id": "x", "text": "t", "freshness_label": "fresh"}])
    with pytest.raises(ValueError):
        synthesize(gw, "m", "q", [])


def test_synthesis_empty_sentences_is_a_typed_failure():
    # zero sentences must never parse into an 'ungrounded_count=0' empty answer —
    # that is the same machine-readable signal as a perfectly grounded one
    gw = StubGateway({"sentences": []})
    with pytest.raises(EmptySynthesisError):
        synthesize(gw, "m", "q",
                   [{"passage_id": "x", "text": "t", "freshness_label": "fresh"}])


def test_golden_corpus_planted_freshness_labels_hold():
    _, _, timestamps = _corpus()
    expected = {d["doc_id"]: d["expected_freshness"] for d in GOLDEN["documents"]}
    for doc_id, ts in timestamps.items():
        assert freshness(ts, REF).label == expected[doc_id], doc_id
