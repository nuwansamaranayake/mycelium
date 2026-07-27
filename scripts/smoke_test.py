"""Smoke: real business endpoints with real processing, against a running instance.

Flow: health -> dev fixture -> register principals -> upload a document (keyless connector)
-> ingest the demo folder (keyless connector) -> query as a permitted principal and assert
cited, freshness-labeled results -> query as a forbidden principal and assert the ACL holds.
Requires the database to be up (Standard 2: a health check alone is not a smoke test).
"""
import os
import sys

import httpx

BASE = f"http://{os.getenv('API_HOST', '127.0.0.1')}:{os.getenv('API_PORT', '8000')}"
TOKEN = os.getenv("SMOKE_TEST_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def get(path: str):
    r = httpx.get(BASE + path, headers=HEADERS, timeout=10)
    r.raise_for_status()
    body = r.json()
    assert body, f"{path} returned an empty body"
    return body


def post(path: str, payload: dict, expect: int = 201, headers: dict | None = None):
    r = httpx.post(BASE + path, headers=headers or HEADERS, json=payload, timeout=30)
    assert r.status_code == expect, f"{path}: {r.status_code} {r.text[:200]}"
    return r.json()


def main():
    env = get("/health").get("env")
    if env == "development":
        assert get("/api/v1/demo").get("items"), "demo endpoint returned no items"
    else:
        # Standard 3: fixture data outside development must 503 — and the business
        # assertions below still run, so this smoke gates staging/production too.
        r = httpx.get(BASE + "/api/v1/demo", headers=HEADERS, timeout=10)
        assert r.status_code == 503, \
            f"demo fixture must be disabled outside development, got {r.status_code}"

    # Registration returns each principal's own bearer token; queries authenticate
    # with it (identity binds to the credential, not the request body).
    alice = post("/api/v1/principals", {"name": "smoke-alice"})
    ops = post("/api/v1/principals", {"name": "smoke-ops"})
    alice_headers = {"Authorization": f"Bearer {alice['token']}"}
    ops_headers = {"Authorization": f"Bearer {ops['token']}"}

    doc = post("/api/v1/documents", {
        "title": "Smoke Travel Policy",
        "text": "Business travel is booked through the travel portal.\n\n"
                "Economy class applies to flights under six hours.",
        "doc_timestamp": "2026-06-01T00:00:00+00:00",
        "allowed_principals": ["smoke-alice"],
    })
    assert doc["passages"] > 0, "upload produced no passages"

    folder = post("/api/v1/ingest/folder", {"path": "data/synthetic/folder-demo"})
    assert folder["ingested"] >= 2, "folder connector ingested nothing"

    q = post("/api/v1/query", {
        "principal": "smoke-alice",
        "query": "How is business travel booked and which flights are economy?",
        "top_k": 3,
    }, headers=alice_headers)
    assert q["results"], "query returned no results for a permitted principal"
    top = q["results"][0]
    # keyed on title, not this run's id: smoke reruns accumulate identical documents
    assert top["title"] == "Smoke Travel Policy", "expected the travel policy on top"
    assert top["span"] and top["freshness"]["label"] in ("fresh", "aging", "stale"), \
        "result missing citation span or freshness label"

    # ACL: the travel policy is alice-only; ops must never see it, even asking verbatim
    q2 = post("/api/v1/query", {
        "principal": "smoke-ops",
        "query": "Business travel is booked through the travel portal economy flights",
        "top_k": 10,
    }, headers=ops_headers)
    leaked = [r for r in q2["results"] if r["title"] == "Smoke Travel Policy"]
    assert not leaked, f"ACL LEAK: forbidden document surfaced: {leaked}"

    if TOKEN:
        # identity binding (auth armed): ops' credential must not be able to claim alice
        r = httpx.post(BASE + "/api/v1/query", headers=ops_headers, timeout=30,
                       json={"principal": "smoke-alice", "query": "travel", "top_k": 1})
        assert r.status_code == 403, f"impersonation must be refused, got {r.status_code}"

    print("SMOKE OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SMOKE FAILED: {e}", file=sys.stderr)
        sys.exit(1)
