"""quota: rate limit + per-user/per-conversation caps.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def _has_column(table: str, col: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return col in {c["name"] for c in insp.get_columns(table)}


_NEW_COLS = [
    ("max_rpm", sa.Integer(), "0"),
    ("max_rps", sa.Integer(), "0"),
    ("max_tokens_per_user_per_day", sa.Integer(), "0"),
    ("max_tokens_per_conversation", sa.Integer(), "0"),
]


def upgrade() -> None:
    for name, type_, default in _NEW_COLS:
        if not _has_column("tenant_quotas", name):
            op.add_column(
                "tenant_quotas",
                sa.Column(name, type_, nullable=False, server_default=default),
            )


def downgrade() -> None:
    for name, _t, _d in _NEW_COLS:
        if _has_column("tenant_quotas", name):
            op.drop_column("tenant_quotas", name)
