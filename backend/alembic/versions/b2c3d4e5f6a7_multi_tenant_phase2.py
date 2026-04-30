"""multi-tenant phase-2: tenant_id on observability + audit tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-30 03:00:00.000000

Adds ``tenant_id`` (defaulted to 'default') + index + FK on:
- obs_ingestion_batches
- obs_file_traces
- obs_agent_spans
- obs_hitl_tasks
- audit_logs

Idempotent — checks columns via reflection.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TARGET_TABLES = (
    "obs_ingestion_batches",
    "obs_file_traces",
    "obs_agent_spans",
    "obs_hitl_tasks",
    "audit_logs",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table in TARGET_TABLES:
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "tenant_id" in cols:
            continue
        op.add_column(
            table,
            sa.Column("tenant_id", sa.String(), nullable=False, server_default="default"),
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
    existing_tables = set(inspector.get_table_names())

    for table in reversed(TARGET_TABLES):
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "tenant_id" not in cols:
            continue
        try:
            op.drop_constraint(f"fk_{table}_tenant_id_tenants", table, type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        except Exception:
            pass
        op.drop_column(table, "tenant_id")
