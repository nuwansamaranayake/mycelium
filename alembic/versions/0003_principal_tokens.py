"""Per-principal bearer tokens: query identity binds to a credential, not a body field.

Revision ID: 0003_principal_tokens
Revises: 0002_real_schema
Create Date: 2026-07-27

Adds principals.token (NOT NULL, UNIQUE). 0002 applies app.db.metadata wholesale, so a
fresh database already has the column after 0002; only databases migrated before the
column existed need the ALTER, hence the conditional. Existing principals are backfilled
with freshly generated tokens (re-registration returns them to an admin caller). Table
count is unchanged: EXPECTED_TABLE_COUNT stays 9 (Standard 4).
"""
import secrets
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

revision = "0003_principal_tokens"
down_revision = "0002_real_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("principals")}
    if "token" in cols:
        return
    op.add_column("principals", sa.Column("token", sa.Text(), nullable=True))
    for (pid,) in bind.execute(sa.text("select id from principals")):
        bind.execute(sa.text("update principals set token = :t where id = :i"),
                     {"t": secrets.token_urlsafe(32), "i": pid})
    op.alter_column("principals", "token", existing_type=sa.Text(), nullable=False)
    op.create_unique_constraint("uq_principals_token", "principals", ["token"])


def downgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("principals")}
    if "token" in cols:
        op.drop_column("principals", "token")
