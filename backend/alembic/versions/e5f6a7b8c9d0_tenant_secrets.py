"""tenant_secrets table for per-tenant encrypted credentials.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def upgrade() -> None:
    if _has_table("tenant_secrets"):
        return
    op.create_table(
        "tenant_secrets",
        sa.Column("tenant_id", sa.String(length=64), sa.ForeignKey("tenants.id"), primary_key=True, nullable=False),
        sa.Column("key_name", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("encrypted_value", sa.String(length=4096), nullable=False),
        sa.Column("hint", sa.String(length=64), nullable=False, server_default="***"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_tenant_secrets_tenant_id",
        "tenant_secrets",
        ["tenant_id"],
    )


def downgrade() -> None:
    if not _has_table("tenant_secrets"):
        return
    op.drop_index("ix_tenant_secrets_tenant_id", table_name="tenant_secrets")
    op.drop_table("tenant_secrets")
