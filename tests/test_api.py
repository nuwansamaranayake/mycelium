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
    # flip auth on for in-process tests; the auth tests set token/env explicitly
    from groundwork import Env

    from app.config import settings
    monkeypatch.setattr(settings, "smoke_test_token", "")
    monkeypatch.setattr(settings, "app_env", Env.development)
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


def test_empty_token_outside_development_refuses_typed_503(client, monkeypatch):
    # fail-open guard: an unset SMOKE_TEST_TOKEN is a deploy error outside development
    from groundwork import Env

    from app.config import settings
    monkeypatch.setattr(settings, "app_env", Env.production)
    r = client.post("/api/v1/principals", json={"name": "x"})
    assert r.status_code == 503
    assert "SMOKE_TEST_TOKEN" in r.json()["detail"]
    r2 = client.post("/api/v1/query", json={
        "principal": "alice", "query": "x", "as_of": "2026-06-20T00:00:00+00:00"})
    assert r2.status_code == 503


def test_principal_registration_idempotent_on_name(client):
    a = client.post("/api/v1/principals", json={"name": "dupe"}).json()
    b = client.post("/api/v1/principals", json={"name": "dupe"}).json()
    assert a["created"] is True and b["created"] is False
    assert b["principal_id"] == a["principal_id"]
    assert b["token"] == a["token"]


def test_query_identity_binds_to_principal_token(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "smoke_test_token", "admin-token")
    admin = {"Authorization": "Bearer admin-token"}
    alice = client.post("/api/v1/principals", json={"name": "alice"}, headers=admin).json()
    mallory = client.post("/api/v1/principals", json={"name": "mallory"}, headers=admin).json()
    client.post("/api/v1/documents", json=DOC, headers=admin)
    q = {"principal": "alice", "query": "How is business travel booked?",
         "as_of": "2026-06-20T00:00:00+00:00"}
    # mallory's credential cannot claim alice
    r = client.post("/api/v1/query", json=q,
                    headers={"Authorization": f"Bearer {mallory['token']}"})
    assert r.status_code == 403
    # the shared admin token is not a query identity
    assert client.post("/api/v1/query", json=q, headers=admin).status_code == 401
    # no credential at all is refused
    assert client.post("/api/v1/query", json=q).status_code == 401
    # alice's own credential works and sees her document
    ok = client.post("/api/v1/query", json=q,
                     headers={"Authorization": f"Bearer {alice['token']}"})
    assert ok.status_code == 201 and ok.json()["results"]


def test_get_answer_requires_matching_principal_when_auth_armed(client, monkeypatch):
    from app import routes
    from app.config import settings
    # build an answer with auth off (dev semantics)...
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
                {"text": "Travel is booked through the portal.", "passage_ids": [pid]}]}

    monkeypatch.setattr(routes, "_gateway", lambda: StubGateway())
    aid = client.post("/api/v1/answers", json={"query_id": q["query_id"]}).json()["answer_id"]
    # ...then arm auth: read-back now requires the originating principal's credential
    monkeypatch.setattr(settings, "smoke_test_token", "admin-token")
    admin = {"Authorization": "Bearer admin-token"}
    alice = client.post("/api/v1/principals", json={"name": "alice"}, headers=admin).json()
    eve = client.post("/api/v1/principals", json={"name": "eve"}, headers=admin).json()
    assert client.get(f"/api/v1/answers/{aid}").status_code == 401
    r = client.get(f"/api/v1/answers/{aid}",
                   headers={"Authorization": f"Bearer {eve['token']}"})
    assert r.status_code == 403
    r2 = client.get(f"/api/v1/answers/{aid}",
                    headers={"Authorization": f"Bearer {alice['token']}"})
    assert r2.status_code == 200 and r2.json()["citations"]
    assert client.get(f"/api/v1/answers/{aid}", headers=admin).status_code == 200


def test_folder_ingest_confined_to_ingest_root(client, tmp_path):
    # a real, readable directory outside the configured ingest root is refused
    (tmp_path / "loot.txt").write_text("secret", encoding="utf-8")
    r = client.post("/api/v1/ingest/folder", json={"path": str(tmp_path)})
    assert r.status_code == 422
    assert "ingest root" in r.json()["detail"]


def test_query_openrouter_embedder_without_config_is_typed_503(client, monkeypatch):
    from app.config import settings
    q = {"principal": "alice", "query": "x", "embedder": "openrouter",
         "as_of": "2026-06-20T00:00:00+00:00"}
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    r = client.post("/api/v1/query", json=q)
    assert r.status_code == 503 and "OPENROUTER_API_KEY" in r.json()["detail"]
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "embedding_model", "")
    r2 = client.post("/api/v1/query", json=q)
    assert r2.status_code == 503 and "EMBEDDING_MODEL" in r2.json()["detail"]


def test_empty_synthesis_is_typed_502_and_never_persisted(client, monkeypatch):
    from app import routes
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_reasoning", "stub-model")
    client.post("/api/v1/documents", json=DOC)
    q = client.post("/api/v1/query", json={
        "principal": "alice", "query": "travel portal booking",
        "as_of": "2026-06-20T00:00:00+00:00"}).json()

    class EmptyGateway:
        def complete(self, *, model, messages, json_schema=None, temperature=0.0):
            return {"sentences": []}

    monkeypatch.setattr(routes, "_gateway", lambda: EmptyGateway())
    r = client.post("/api/v1/answers", json={"query_id": q["query_id"]})
    assert r.status_code == 502
    with db.get_session() as s:
        n = s.execute(sa.select(sa.func.count()).select_from(db.answers)).scalar_one()
    assert n == 0, "an empty synthesis must never be recorded as a grounded answer"
