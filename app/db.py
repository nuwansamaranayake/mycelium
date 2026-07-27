"""Schema and session plumbing. metadata is the single source of truth; the alembic
migration applies it, and EXPECTED_TABLE_COUNT asserts the result (Standard 4)."""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

from .config import settings

JSON = sa.JSON().with_variant(JSONB(), "postgresql")

metadata = sa.MetaData()

documents = sa.Table(
    "documents", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("external_id", sa.Text),                    # path or upload name
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("source", sa.Text, nullable=False),         # folder | upload
    sa.Column("doc_timestamp", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

passages = sa.Table(
    "passages", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
    sa.Column("ordinal", sa.Integer, nullable=False),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("span_start", sa.Integer, nullable=False),
    sa.Column("span_end", sa.Integer, nullable=False),
)

principals = sa.Table(
    "principals", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text, nullable=False, unique=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

acl_entries = sa.Table(
    "acl_entries", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
    sa.Column("principal", sa.Text, nullable=False),      # principal name, or * for everyone
)

queries = sa.Table(
    "queries", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("principal", sa.Text, nullable=False),
    sa.Column("query_text", sa.Text, nullable=False),
    sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

retrievals = sa.Table(
    "retrievals", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("query_id", sa.Integer, sa.ForeignKey("queries.id"), nullable=False),
    sa.Column("passage_id", sa.Integer, sa.ForeignKey("passages.id"), nullable=False),
    sa.Column("rank", sa.Integer, nullable=False),
    sa.Column("bm25_score", sa.Float, nullable=False),
    sa.Column("cosine_score", sa.Float, nullable=False),
    sa.Column("fused_score", sa.Float, nullable=False),
    sa.Column("freshness_label", sa.Text, nullable=False),  # fresh | aging | stale
    sa.Column("age_days", sa.Integer, nullable=False),
)

answers = sa.Table(
    "answers", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("query_id", sa.Integer, sa.ForeignKey("queries.id"), nullable=False),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("model", sa.Text, nullable=False),
    sa.Column("ungrounded_count", sa.Integer, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

answer_citations = sa.Table(
    "answer_citations", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("answer_id", sa.Integer, sa.ForeignKey("answers.id"), nullable=False),
    sa.Column("passage_id", sa.Integer, sa.ForeignKey("passages.id"), nullable=False),
    sa.Column("sentence_index", sa.Integer, nullable=False),
    sa.Column("sentence_text", sa.Text, nullable=False),
)

_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        _engine = sa.create_engine(settings.database_url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine)
    return _engine


def get_session():
    get_engine()
    return _Session()


def set_engine_for_tests(engine) -> None:
    """Tests inject their own engine (sqlite in-memory). Explicit, never automatic."""
    global _engine, _Session
    _engine = engine
    _Session = sessionmaker(bind=engine)
