"""Migration: add max_cost_usd_micro_per_day + warn_threshold_pct to tenant_quotas."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tenant_quotas" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("tenant_quotas")}
    if "max_cost_usd_micro_per_day" not in cols:
        op.add_column(
            "tenant_quotas",
            sa.Column("max_cost_usd_micro_per_day", sa.BigInteger(),
                      nullable=False, server_default="0"),
        )
    if "warn_threshold_pct" not in cols:
        op.add_column(
            "tenant_quotas",
            sa.Column("warn_threshold_pct", sa.Integer(),
                      nullable=False, server_default="80"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tenant_quotas" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("tenant_quotas")}
    if "warn_threshold_pct" in cols:
        op.drop_column("tenant_quotas", "warn_threshold_pct")
    if "max_cost_usd_micro_per_day" in cols:
        op.drop_column("tenant_quotas", "max_cost_usd_micro_per_day")
