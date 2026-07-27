"""Business endpoints: ingest -> ACL-filtered hybrid retrieval -> cited answers, persisted.

POST /api/v1/principals       register a principal (identity for ACL checks)
POST /api/v1/documents        direct upload connector (keyless product path)
POST /api/v1/ingest/folder    folder connector: .txt/.md files + optional manifest (keyless)
POST /api/v1/query            hybrid retrieval; every result cites doc id + span + freshness
POST /api/v1/answers          LLM answer synthesis over a stored query (key-gated)
GET  /api/v1/answers/{id}     stored answer with citations (principal-gated read-back)

The keyless connectors and retrieval are real product features; the LLM synthesis path
refuses loudly without a key — no silent fallback between the two (Standard 3). Staleness
labels are computed against the as_of carried by the query; datetime.now() appears only as
the live-API default for as_of, never in eval paths.

Auth model (Phase 1): the shared SMOKE_TEST_TOKEN guards mutations; registration issues a
per-principal bearer token, and /query plus answer read-back derive identity from that
credential — never from the request body alone. An empty SMOKE_TEST_TOKEN turns auth off
in development only; every other environment gets a typed 503 (Standard 3, no fail-open).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Header, HTTPException
from groundwork import BaseConfig, Env, LLMGateway
from pydantic import BaseModel, Field

from . import db
from .config import settings
from .connectors.folder import ingest_folder
from .engine.embedding import HashingEmbedder, OpenRouterEmbedder
from .engine.freshness import freshness
from .engine.retrieval import CorpusPassage, retrieve
from .engine.synthesis import EmptySynthesisError, synthesize

router = APIRouter(prefix="/api/v1")


def _auth_disabled() -> bool:
    """Empty SMOKE_TEST_TOKEN means auth is off — a development-only convenience.
    Outside development that configuration is a deploy error, not a default: refuse
    loudly (Standard 3), mirroring the /api/v1/demo prod guard in main.py."""
    if settings.smoke_test_token:
        return False
    if settings.app_env is not Env.development:
        raise HTTPException(
            status_code=503,
            detail="SMOKE_TEST_TOKEN is not set; serving without auth is allowed only "
                   "in development. Set SMOKE_TEST_TOKEN for this environment.")
    return True


def _auth(authorization: str | None) -> None:
    """Shared admin token: guards mutations (principals, documents, ingest, answers)."""
    if _auth_disabled():
        return
    if authorization != f"Bearer {settings.smoke_test_token}":
        raise HTTPException(status_code=401, detail="missing or invalid bearer token")


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization.removeprefix("Bearer ")


def _bind_principal(s, authorization: str | None, claimed: str) -> str:
    """Query identity comes from the credential, never the request body alone. With auth
    armed, the bearer token must be the per-principal token issued at registration and
    must belong to the claimed principal. With auth off (development only, enforced by
    _auth_disabled) the claimed principal is trusted — documented dev semantics."""
    if _auth_disabled():
        return claimed
    token = _bearer(authorization)
    row = s.execute(sa.select(db.principals.c.name)
                    .where(db.principals.c.token == token)).first()
    if row is None:
        raise HTTPException(status_code=401, detail="unknown principal token")
    if row[0] != claimed:
        raise HTTPException(
            status_code=403,
            detail="principal in body does not match the authenticated principal")
    return row[0]


def _gateway() -> LLMGateway:
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="answer synthesis requires OPENROUTER_API_KEY; the /api/v1/query "
                   "endpoint is the keyless retrieval path",
        )
    return LLMGateway(BaseConfig(
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_base_url=settings.openrouter_base_url,
    ))


def _embedder(name: str):
    if name == "openrouter":
        # Same typed refusal as _gateway: a missing variable is a 503 naming it,
        # never an opaque 500 from a constructor RuntimeError.
        if not settings.openrouter_api_key:
            raise HTTPException(
                status_code=503,
                detail="embedder 'openrouter' requires OPENROUTER_API_KEY; "
                       "the default 'hashing' embedder is the keyless path")
        if not settings.embedding_model:
            raise HTTPException(
                status_code=503,
                detail="embedder 'openrouter' requires EMBEDDING_MODEL; "
                       "refusing to guess a model")
        return OpenRouterEmbedder(
            api_key=settings.openrouter_api_key,
            model=settings.embedding_model,
            base_url=settings.openrouter_base_url,
        )
    return HashingEmbedder()


def _store_document(s, *, external_id: str | None, title: str, text: str, source: str,
                    doc_timestamp: datetime, allowed_principals: list[str]) -> tuple[int, int]:
    from .engine.chunking import chunk_document
    did = s.execute(db.documents.insert().values(
        external_id=external_id, title=title, text=text, source=source,
        doc_timestamp=doc_timestamp)).inserted_primary_key[0]
    chunks = chunk_document(text)
    for c in chunks:
        s.execute(db.passages.insert().values(
            document_id=did, ordinal=c.ordinal, text=c.text,
            span_start=c.span_start, span_end=c.span_end))
    for principal in allowed_principals:
        s.execute(db.acl_entries.insert().values(document_id=did, principal=principal))
    return did, len(chunks)


def _aware(dt: datetime) -> datetime:
    """Values are stored timezone-aware (UTC); sqlite discards tzinfo on the way back.
    Re-attach UTC at the load boundary so freshness math keeps refusing naive input."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _load_corpus(s):
    """DB rows -> the same in-memory shapes the engine and eval use."""
    doc_rows = s.execute(sa.select(db.documents)).mappings().all()
    acl_rows = s.execute(sa.select(db.acl_entries)).mappings().all()
    passage_rows = s.execute(sa.select(db.passages)).mappings().all()
    titles = {str(d["id"]): d["title"] for d in doc_rows}
    timestamps = {str(d["id"]): _aware(d["doc_timestamp"]) for d in doc_rows}
    acls: dict[str, set[str]] = {str(d["id"]): set() for d in doc_rows}
    for a in acl_rows:
        acls[str(a["document_id"])].add(a["principal"])
    corpus = [CorpusPassage(
        passage_id=str(p["id"]), doc_id=str(p["document_id"]), text=p["text"],
        span_start=p["span_start"], span_end=p["span_end"],
        title=titles[str(p["document_id"])]) for p in passage_rows]
    return corpus, acls, timestamps, titles


class PrincipalIn(BaseModel):
    name: str = Field(min_length=1)


class DocumentIn(BaseModel):
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    doc_timestamp: datetime
    allowed_principals: list[str] = Field(min_length=1)
    external_id: str | None = None


class FolderIn(BaseModel):
    path: str = Field(min_length=1)


class QueryIn(BaseModel):
    principal: str = Field(min_length=1)
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    as_of: datetime | None = None
    embedder: str = Field(default="hashing", pattern="^(hashing|openrouter)$")


class AnswerIn(BaseModel):
    query_id: int


@router.post("/principals", status_code=201)
def create_principal(body: PrincipalIn, authorization: str | None = Header(default=None)):
    """Admin-gated registration. Issues the per-principal bearer token that /query and
    answer read-back authenticate with. Idempotent on name: the unique constraint is
    the arbiter — insert first, never check-then-insert (that races under concurrency).
    Re-registering returns the existing id and token (the caller already holds admin)."""
    _auth(authorization)
    token = secrets.token_urlsafe(32)
    try:
        with db.get_session() as s, s.begin():
            pid = s.execute(db.principals.insert().values(
                name=body.name, token=token)).inserted_primary_key[0]
        return {"principal_id": pid, "created": True, "token": token}
    except sa.exc.IntegrityError:
        with db.get_session() as s:
            row = s.execute(sa.select(db.principals.c.id, db.principals.c.token)
                            .where(db.principals.c.name == body.name)).first()
        if row is None:  # pragma: no cover — conflict was not on name; surface it
            raise
        return {"principal_id": row[0], "created": False, "token": row[1]}


@router.post("/documents", status_code=201)
def upload_document(body: DocumentIn, authorization: str | None = Header(default=None)):
    _auth(authorization)
    if body.doc_timestamp.tzinfo is None:
        raise HTTPException(status_code=422, detail="doc_timestamp must carry a timezone")
    with db.get_session() as s, s.begin():
        did, n = _store_document(
            s, external_id=body.external_id, title=body.title, text=body.text,
            source="upload", doc_timestamp=body.doc_timestamp,
            allowed_principals=body.allowed_principals)
    return {"document_id": did, "passages": n}


@router.post("/ingest/folder", status_code=201)
def ingest_from_folder(body: FolderIn, authorization: str | None = Header(default=None)):
    _auth(authorization)
    try:
        docs = ingest_folder(body.path, ingest_root=settings.ingest_root)
    except (FileNotFoundError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    stored = []
    with db.get_session() as s, s.begin():
        for d in docs:
            did, n = _store_document(
                s, external_id=d.external_id, title=d.title, text=d.text, source="folder",
                doc_timestamp=d.doc_timestamp, allowed_principals=d.allowed_principals)
            stored.append({"document_id": did, "external_id": d.external_id, "passages": n})
    return {"ingested": len(stored), "documents": stored}


@router.post("/query", status_code=201)
def run_query(body: QueryIn, authorization: str | None = Header(default=None)):
    embedder = _embedder(body.embedder)
    # the ONLY place wall-clock enters staleness math: the live-API default
    as_of = body.as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise HTTPException(status_code=422, detail="as_of must carry a timezone")
    # Read phase: bind identity and load the corpus, then release the connection.
    # Retrieval may call a network embedder and must never run inside an open
    # transaction — a 60s HTTP call pinning a pooled connection starves the pool.
    with db.get_session() as s:
        principal = _bind_principal(s, authorization, body.principal)
        corpus, acls, timestamps, titles = _load_corpus(s)
    hits = retrieve(body.query, corpus, principal, acls, embedder, body.top_k)
    by_id = {p.passage_id: p for p in corpus}
    results = []
    retrieval_rows = []
    for h in hits:
        fl = freshness(timestamps[h.doc_id], as_of)
        p = by_id[h.passage_id]
        retrieval_rows.append({
            "passage_id": int(h.passage_id), "rank": h.rank,
            "bm25_score": h.bm25_score, "cosine_score": h.cosine_score,
            "fused_score": h.fused_score, "freshness_label": fl.label,
            "age_days": fl.age_days})
        results.append({
            "passage_id": int(h.passage_id), "document_id": int(h.doc_id),
            "title": titles[h.doc_id], "text": p.text,
            "span": [p.span_start, p.span_end], "rank": h.rank,
            "bm25_score": h.bm25_score, "cosine_score": h.cosine_score,
            "fused_score": h.fused_score,
            "freshness": {"label": fl.label, "age_days": fl.age_days}})
    # Write phase: a short transaction for the query and its retrievals only.
    with db.get_session() as s, s.begin():
        qid = s.execute(db.queries.insert().values(
            principal=principal, query_text=body.query,
            as_of=as_of)).inserted_primary_key[0]
        for row in retrieval_rows:
            s.execute(db.retrievals.insert().values(query_id=qid, **row))
    return {"query_id": qid, "as_of": as_of.isoformat(), "results": results}


@router.post("/answers", status_code=201)
def create_answer(body: AnswerIn, authorization: str | None = Header(default=None)):
    _auth(authorization)
    gateway = _gateway()
    if not settings.llm_model_reasoning:
        raise HTTPException(status_code=503,
                            detail="LLM_MODEL_REASONING is not set; refusing to guess a model")
    # Read phase: load the query and its retrievals, then release the connection —
    # the LLM round-trip (up to LLM_TIMEOUT_SECONDS) must not hold a transaction open.
    with db.get_session() as s:
        q = s.execute(sa.select(db.queries)
                      .where(db.queries.c.id == body.query_id)).mappings().first()
        if q is None:
            raise HTTPException(status_code=404, detail="query not found")
        rows = s.execute(
            sa.select(db.retrievals, db.passages.c.text)
            .join(db.passages, db.retrievals.c.passage_id == db.passages.c.id)
            .where(db.retrievals.c.query_id == body.query_id)
            .order_by(db.retrievals.c.rank)).mappings().all()
    if not rows:
        raise HTTPException(status_code=422,
                            detail="query has no retrieved passages to answer from")
    passages = [{"passage_id": str(r["passage_id"]), "text": r["text"],
                 "freshness_label": r["freshness_label"]} for r in rows]
    try:
        answer = synthesize(gateway, settings.llm_model_reasoning, q["query_text"], passages)
    except EmptySynthesisError as e:
        raise HTTPException(status_code=502, detail=str(e))
    # Write phase: a short transaction for the answer and its citations only.
    with db.get_session() as s, s.begin():
        aid = s.execute(db.answers.insert().values(
            query_id=body.query_id, text=answer.text,
            model=settings.llm_model_reasoning,
            ungrounded_count=answer.ungrounded_count)).inserted_primary_key[0]
        for i, sent in enumerate(answer.sentences):
            for pid in sent.passage_ids:
                if sent.grounded:
                    s.execute(db.answer_citations.insert().values(
                        answer_id=aid, passage_id=int(pid), sentence_index=i,
                        sentence_text=sent.text))
    return {"answer_id": aid, "text": answer.text,
            "ungrounded_count": answer.ungrounded_count,
            "model": settings.llm_model_reasoning,
            "sentences": [s_.model_dump() for s_ in answer.sentences]}


@router.get("/answers/{aid}")
def get_answer(aid: int, authorization: str | None = Header(default=None)):
    """Answers are synthesized from ACL-filtered passages for the originating query's
    principal — read-back is gated on that same principal (or the admin token). An
    unauthenticated GET here would leak restricted corpus content by guessing ids."""
    with db.get_session() as s:
        row = s.execute(
            sa.select(db.answers, db.queries.c.principal)
            .join(db.queries, db.answers.c.query_id == db.queries.c.id)
            .where(db.answers.c.id == aid)).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="answer not found")
        if not _auth_disabled():
            token = _bearer(authorization)
            if token != settings.smoke_test_token:
                p = s.execute(sa.select(db.principals.c.name)
                              .where(db.principals.c.token == token)).first()
                if p is None:
                    raise HTTPException(status_code=401, detail="unknown principal token")
                if p[0] != row["principal"]:
                    raise HTTPException(
                        status_code=403,
                        detail="answer belongs to a different principal")
        cites = s.execute(sa.select(db.answer_citations)
                          .where(db.answer_citations.c.answer_id == aid)
                          .order_by(db.answer_citations.c.sentence_index)).mappings().all()
    answer = {k: v for k, v in dict(row).items() if k != "principal"}
    return {"answer": answer, "citations": [dict(c) for c in cites]}
