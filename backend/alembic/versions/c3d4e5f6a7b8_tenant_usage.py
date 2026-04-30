"""Migration: tenant_usage_daily + indexes."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tenant_usage_daily" not in inspector.get_table_names():
        op.create_table(
            "tenant_usage_daily",
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), primary_key=True),
            sa.Column("usage_date", sa.Date(), primary_key=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cost_usd_micro", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("last_updated", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_tenant_usage_daily_date", "tenant_usage_daily", ["usage_date"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tenant_usage_daily" in inspector.get_table_names():
        try:
            op.drop_index("ix_tenant_usage_daily_date", table_name="tenant_usage_daily")
        except Exception:
            pass
        op.drop_table("tenant_usage_daily")
