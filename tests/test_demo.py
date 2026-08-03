"""Part C: demo access on the shared kit, proven — and the claim the demo rests on:
the restricted principal cannot retrieve the restricted document, with the exclusion
counted before scoring.
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from groundwork.testing import FakeRedis

from app import db, demo
from app.config import settings
from app.main import app

ADMIN = "estate-token"
H = {"Authorization": f"Bearer {ADMIN}"}


@pytest.fixture()
def client(monkeypatch):
    engine = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                              connect_args={"check_same_thread": False})
    db.metadata.create_all(engine)
    db.set_engine_for_tests(engine)
    monkeypatch.setattr(settings, "smoke_test_token", ADMIN)
    fake = FakeRedis()
    demo.set_redis_for_tests(fake)
    c = TestClient(app)
    c.fake_redis = fake
    return c


def _session(client) -> dict:
    r = client.post("/api/v1/demo/session")
    assert r.status_code == 201, r.text
    return r.json()


def _query(client, principal: dict, q: str):
    return client.post("/api/v1/query",
                       json={"principal": principal["name"], "query": q},
                       headers={"Authorization": f"Bearer {principal['token']}"})


def test_session_seeds_two_principals_and_four_documents(client):
    s = _session(client)
    assert s["synthetic"] is True
    assert {p["role"] for p in s["principals"]} == {"broad", "restricted"}
    assert len(s["documents"]) == 4
    assert sum(1 for d in s["documents"] if d["restricted_to_broad"]) == 1


def test_the_restricted_principal_cannot_retrieve_the_restricted_document(client):
    """G2's claim, at unit level: not in the results, and excluded BEFORE scoring."""
    s = _session(client)
    broad = next(p for p in s["principals"] if p["role"] == "broad")
    restricted = next(p for p in s["principals"] if p["role"] == "restricted")
    q = "How often is the vault master password rotated?"

    rb = _query(client, broad, q).json()
    assert any("RESTRICTED" in r["title"] for r in rb["results"]), \
        "the broad principal must see the runbook"
    assert rb["acl"]["excluded_documents"] == 0

    rr = _query(client, restricted, q).json()
    assert not any("RESTRICTED" in r["title"] for r in rr["results"]), \
        "the restricted principal saw the restricted document: the demo's core claim fails"
    assert rr["acl"]["excluded_documents"] >= 1
    assert rr["acl"]["filtered_before_scoring"] is True


def test_stale_and_fresh_labels_disagree_on_the_deploy_question(client):
    s = _session(client)
    broad = next(p for p in s["principals"] if p["role"] == "broad")
    r = _query(client, broad, "How do production deploys work?").json()
    labels = {x["title"]: x["freshness"]["label"] for x in r["results"]}
    assert any("2023" in t and lbl == "stale" for t, lbl in labels.items()), labels
    assert any("current" in t and lbl == "fresh" for t, lbl in labels.items()), labels


def test_principal_tokens_are_real_auth_not_demo_semantics(client):
    """A wrong token for the claimed principal is refused on the production path."""
    s = _session(client)
    broad = next(p for p in s["principals"] if p["role"] == "broad")
    restricted = next(p for p in s["principals"] if p["role"] == "restricted")
    r = client.post("/api/v1/query",
                    json={"principal": broad["name"], "query": "x"},
                    headers={"Authorization": f"Bearer {restricted['token']}"})
    assert r.status_code in (401, 403)


def test_demo_query_budget_is_a_counter_that_refuses(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_request_budget", 2)
    s = _session(client)
    broad = next(p for p in s["principals"] if p["role"] == "broad")
    assert _query(client, broad, "vpn?").status_code == 201
    assert _query(client, broad, "vpn?").status_code == 201
    assert _query(client, broad, "vpn?").status_code == 429


def test_every_seeded_row_is_tenant_prefixed_for_retention(client):
    _session(client)
    with db.get_session() as s:
        titles = [r.title for r in s.execute(sa.select(db.documents.c.title)).all()]
        names = [r.name for r in s.execute(sa.select(db.principals.c.name)).all()]
    import re
    shape = re.compile(r"^demo-\d{8}T\d{6}Z-[0-9a-f]{6}-")
    assert titles and all(shape.match(t) for t in titles)
    assert names and all(shape.match(n) for n in names)


def test_session_creation_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_sessions_per_ip_hour", 2)
    _session(client)
    _session(client)
    assert client.post("/api/v1/demo/session").status_code == 429
