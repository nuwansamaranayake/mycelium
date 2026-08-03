"""Demo access for Mycelium, on the shared kit (groundwork.demokit).

Sessions, tenant prefixes, budgets and TTLs come from groundwork v0.2.0 — extracted from
CareerCompiler after it shipped, applied here as product three. What lives in this module
is Mycelium-specific: the seeded corpus that makes the thesis visible without typing, and
the per-principal query budget (synthesis costs LLM tokens, and Mycelium authenticates
queries with per-principal tokens rather than the session token).

The seed is designed so every demo moment exists the instant a session opens:

- a RESTRICTED document only the broad principal may see (the ACL refusal moment),
- a stale document and a fresh one that materially disagree on the same question
  (the warranty label and the disagreement, in one pair),
- a fresh document that answers a common question cleanly,
- and no document at all about parental leave (the honest miss).

All titles and principal names carry the tenant prefix, so scope checks are string
comparisons and the portfolio-ops retention sweep reclaims every row by prefix match.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

import redis as redis_lib
from groundwork import DemoKit, DemoRefused

from . import db
from .config import settings

_client = None
_kit: DemoKit | None = None


def get_redis():
    global _client
    if _client is None:
        _client = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def set_redis_for_tests(client) -> None:
    global _client, _kit
    _client = client
    _kit = None


def kit() -> DemoKit:
    global _kit
    if _kit is None:
        _kit = DemoKit(get_redis(),
                       ttl_seconds=settings.demo_session_ttl_seconds,
                       request_budget=settings.demo_request_budget,
                       sessions_per_ip_hour=settings.demo_sessions_per_ip_hour)
    return _kit


def check_query_budget(principal: str) -> None:
    """Queries authenticate with per-principal tokens, so the session budget cannot see
    them; demo principals get their own counter. Same window, same refusal, same honesty:
    a spent budget is a 429, not a slow fade."""
    if not principal.startswith("demo-"):
        return
    r = get_redis()
    key = f"demo:q:{principal}"
    n = r.incr(key)
    if n == 1:
        r.expire(key, settings.demo_session_ttl_seconds)
    if n > settings.demo_request_budget:
        raise DemoRefused(429, "demo query budget exhausted; open a new session")


# ------------------------------------------------------------------------- seed (C2/C3)
BROAD = "broad-access"
RESTRICTED = "restricted-contractor"

_NOW_TEXT_FRESH = (
    "Deploy Process (current). Production deploys run through GitHub Actions: every merge "
    "to main builds the image, runs the test suite, and a smoke test against staging must "
    "pass before the deploy job promotes to production. Rollback is one workflow dispatch. "
    "The on-call engineer approves the promote step during business hours.")

_TEXT_STALE = (
    "Deploy Process. Production deploys are run through Jenkins: the release manager "
    "triggers the deploy pipeline by hand after the weekly change-approval board meeting. "
    "Rollback requires restoring the previous WAR file from the artifact share.")

_TEXT_RESTRICTED = (
    "Incident Response Runbook. RESTRICTED distribution. The production database failover "
    "credentials live in the operations vault, and the vault master password is rotated "
    "every 30 days by the infrastructure lead. During a failover, page the on-call DBA "
    "before touching the replica promotion script.")

_TEXT_FAQ = (
    "Onboarding FAQ. VPN access: request the corporate VPN profile in the IT portal under "
    "Access Requests; approval normally lands within one business day, and the profile "
    "works on both laptop and phone. Your manager is the approver.")

SUGGESTED_QUESTIONS = [
    {"q": "How do production deploys work?",
     "shows": "conflicting answers with fresh and stale warranty labels"},
    {"q": "How often is the vault master password rotated?",
     "shows": "answered for the broad principal; refused evidence for the restricted one"},
    {"q": "How do I get VPN access?", "shows": "a clean fresh answer with a citation"},
    {"q": "What is the parental leave policy?",
     "shows": "the honest miss - no fluent guess"},
]


def seed_tenant(s, prefix: str, store_document) -> dict:
    """Two principals with their own bearer tokens, four documents, zero LLM calls.

    `store_document` is routes._store_document, passed in to keep the dependency
    one-directional. Principal tokens are returned to the browser: the UI's principal
    switcher just changes which bearer it sends, so the ACL demo runs on the same
    authentication path production uses — no demo-only query semantics.
    """
    now = datetime.now(timezone.utc)
    principals = {}
    for short in (BROAD, RESTRICTED):
        name = f"{prefix}{short}"
        token = secrets.token_urlsafe(32)
        s.execute(db.principals.insert().values(name=name, token=token))
        principals[short] = {"name": name, "token": token}

    broad = principals[BROAD]["name"]
    restricted = principals[RESTRICTED]["name"]

    docs = [
        ("Incident Response Runbook (RESTRICTED)", _TEXT_RESTRICTED,
         now.replace(year=now.year - 0), [broad]),                       # broad only
        ("Deploy Process (2023, superseded)", _TEXT_STALE,
         now.replace(year=now.year - 3), [broad, restricted]),           # stale
        ("Deploy Process (current)", _NOW_TEXT_FRESH, now, [broad, restricted]),
        ("Onboarding FAQ", _TEXT_FAQ, now, [broad, restricted]),
    ]
    seeded = []
    for title, text, ts, acl in docs:
        did, chunks = store_document(
            s, external_id=None, title=f"{prefix}{title}", text=text,
            source="demo-seed", doc_timestamp=ts, allowed_principals=acl)
        seeded.append({"document_id": did, "title": title, "chunks": chunks,
                       "restricted_to_broad": acl == [broad]})

    return {"principals": [
                {"role": "broad", "name": broad, "display": "Broad access",
                 "token": principals[BROAD]["token"]},
                {"role": "restricted", "name": restricted,
                 "display": "Restricted contractor",
                 "token": principals[RESTRICTED]["token"]}],
            "documents": seeded,
            "suggested_questions": SUGGESTED_QUESTIONS,
            "synthetic": True}
