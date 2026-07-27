import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app import db
from app.main import app

DOC = {
    "title": "Travel Policy",
    "text": "Business travel is booked through the travel portal.\n\n"
            "Economy class applies to flights under six hours.",
    "doc_timestamp": "2026-06-01T00:00:00+00:00",
    "allowed_principals": ["alice"],
}


@pytest.fixture()
def client(monkeypatch):
    engine = sa.create_engine(
        "sqlite://",
        poolclass=sa.pool.StaticPool,
        connect_args={"check_same_thread": False},   # TestClient serves on another thread
    )
    db.metadata.create_all(engine)
    db.set_engine_for_tests(engine)
    # hermetic: ambient SMOKE_TEST_TOKEN (e.g. exported for the gate's live smoke) must not
    # flip auth on for in-process tests; the auth test sets it explicitly
    from app.config import settings
    monkeypatch.setattr(settings, "smoke_test_token", "")
    return TestClient(app)


def test_upload_query_loop_with_citation_and_freshness(client):
    did = client.post("/api/v1/documents", json=DOC).json()["document_id"]
    r = client.post("/api/v1/query", json={
        "principal": "alice", "query": "How is business travel booked?",
        "as_of": "2026-06-20T00:00:00+00:00", "top_k": 3})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["results"], "no results for a permitted principal"
    top = body["results"][0]
    assert top["document_id"] == did
    # the citation is checkable: span text equals the passage text
    s, e = top["span"]
    assert DOC["text"][s:e] == top["text"]
    # planted timestamp 2026-06-01, as_of 2026-06-20 -> 19 days -> fresh
    assert top["freshness"] == {"label": "fresh", "age_days": 19}


def test_query_acl_excludes_forbidden_document(client):
    client.post("/api/v1/documents", json=DOC)
    r = client.post("/api/v1/query", json={
        "principal": "mallory",
        "query": "Business travel is booked through the travel portal",
        "as_of": "2026-06-20T00:00:00+00:00", "top_k": 10})
    assert r.status_code == 201
    assert r.json()["results"] == [], "ACL leak: forbidden document surfaced"


def test_folder_connector_ingests_demo_folder(client):
    r = client.post("/api/v1/ingest/folder", json={"path": "data/synthetic/folder-demo"})
    assert r.status_code == 201, r.text
    assert r.json()["ingested"] == 2
    # manifest ACLs hold: the on-call handbook is ops-only
    q = client.post("/api/v1/query", json={
        "principal": "ops", "query": "Who carries the pager in the on-call rotation?",
        "as_of": "2026-07-01T00:00:00+00:00"})
    docs = {res["title"] for res in q.json()["results"]}
    assert "On-call Handbook" in docs
    q2 = client.post("/api/v1/query", json={
        "principal": "alice", "query": "Who carries the pager in the on-call rotation?",
        "as_of": "2026-07-01T00:00:00+00:00", "top_k": 10})
    assert all(res["title"] != "On-call Handbook" for res in q2.json()["results"])


def test_answers_without_key_fail_loud(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    client.post("/api/v1/documents", json=DOC)
    qid = client.post("/api/v1/query", json={
        "principal": "alice", "query": "travel portal booking",
        "as_of": "2026-06-20T00:00:00+00:00"}).json()["query_id"]
    r = client.post("/api/v1/answers", json={"query_id": qid})
    assert r.status_code == 503
    assert "OPENROUTER_API_KEY" in r.json()["detail"]


def test_answer_synthesis_with_stub_gateway_persists_citations(client, monkeypatch):
    from app import routes
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_reasoning", "stub-model")
    client.post("/api/v1/documents", json=DOC)
    q = client.post("/api/v1/query", json={
        "principal": "alice", "query": "How is business travel booked?",
        "as_of": "2026-06-20T00:00:00+00:00"}).json()
    pid = str(q["results"][0]["passage_id"])

    class StubGateway:
        def complete(self, *, model, messages, json_schema=None, temperature=0.0):
            return {"sentences": [
                {"text": "Travel is booked through the portal.", "passage_ids": [pid]},
                {"text": "Uncited speculation.", "passage_ids": []},
            ]}

    monkeypatch.setattr(routes, "_gateway", lambda: StubGateway())
    r = client.post("/api/v1/answers", json={"query_id": q["query_id"]})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ungrounded_count"] == 1
    stored = client.get(f"/api/v1/answers/{body['answer_id']}").json()
    assert stored["answer"]["ungrounded_count"] == 1
    assert [c["passage_id"] for c in stored["citations"]] == [int(pid)]


def test_bearer_auth_enforced_when_token_set(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "smoke_test_token", "sekrit")
    assert client.post("/api/v1/principals", json={"name": "x"}).status_code == 401
    assert client.post("/api/v1/principals", json={"name": "x"},
                       headers={"Authorization": "Bearer sekrit"}).status_code == 201


def test_naive_timestamp_rejected(client):
    bad = dict(DOC, doc_timestamp="2026-06-01T00:00:00")
    assert client.post("/api/v1/documents", json=bad).status_code == 422
