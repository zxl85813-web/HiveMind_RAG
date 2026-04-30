"""multi-tenant: add tenants table + tenant_id columns

Revision ID: a1b2c3d4e5f6
Revises: 3a93207357a7
Create Date: 2026-04-30 02:00:00.000000

Adds:
- ``tenants`` table (with default 'default' tenant seed for backward compat).
- ``tenant_quotas`` table (per-tenant limits).
- ``tenant_id`` columns on ``users`` / ``conversations`` /
  ``knowledge_bases`` / ``documents`` — defaulted to 'default' so
  pre-multi-tenant rows remain valid.

Idempotent: uses ``op.execute`` with ``IF NOT EXISTS`` style guards via
SQLAlchemy reflection where possible.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "3a93207357a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_TENANT_ID = "default"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. tenants table -----------------------------------------------------
    if "tenants" not in inspector.get_table_names():
        op.create_table(
            "tenants",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("slug", sa.String(64), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("plan", sa.String(32), nullable=False, server_default="free"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("settings_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # 2. tenant_quotas table ----------------------------------------------
    if "tenant_quotas" not in inspector.get_table_names():
        op.create_table(
            "tenant_quotas",
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), primary_key=True),
            sa.Column("max_users", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("max_conversations_per_day", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("max_subagents_concurrent", sa.Integer(), nullable=False, server_default="4"),
            sa.Column("max_tokens_per_day", sa.Integer(), nullable=False, server_default="1000000"),
            sa.Column("max_kb_count", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # 3. seed the default tenant so existing rows have a valid FK ----------
    op.execute(
        sa.text(
            "INSERT INTO tenants (id, slug, name, plan) "
            "VALUES (:id, :slug, :name, 'enterprise') "
            "ON CONFLICT (id) DO NOTHING"
        ).bindparams(id=DEFAULT_TENANT_ID, slug=DEFAULT_TENANT_ID, name="Default Tenant")
    )

    # 4. add tenant_id columns to existing tables --------------------------
    for table in ("users", "conversations", "knowledge_bases", "documents"):
        if table not in inspector.get_table_names():
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        if "tenant_id" not in existing_cols:
            op.add_column(
                table,
                sa.Column(
                    "tenant_id",
                    sa.String(),
                    nullable=False,
                    server_default=DEFAULT_TENANT_ID,
                ),
            )
            op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
            op.create_foreign_key(
                f"fk_{table}_tenant_id_tenants",
                table,
                "tenants",
                ["tenant_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in ("documents", "knowledge_bases", "conversations", "users"):
        if table not in inspector.get_table_names():
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        if "tenant_id" in existing_cols:
            try:
                op.drop_constraint(f"fk_{table}_tenant_id_tenants", table, type_="foreignkey")
            except Exception:
                pass
            try:
                op.drop_index(f"ix_{table}_tenant_id", table_name=table)
            except Exception:
                pass
            op.drop_column(table, "tenant_id")

    if "tenant_quotas" in inspector.get_table_names():
        op.drop_table("tenant_quotas")
    if "tenants" in inspector.get_table_names():
        try:
            op.drop_index("ix_tenants_slug", table_name="tenants")
        except Exception:
            pass
        op.drop_table("tenants")
