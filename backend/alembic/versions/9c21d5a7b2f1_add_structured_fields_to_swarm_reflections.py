"""Add structured fields to swarm reflections

Revision ID: 9c21d5a7b2f1
Revises: 3a93207357a7
Create Date: 2026-03-10 12:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c21d5a7b2f1"
down_revision: str | None = "3a93207357a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "swarm_reflections",
        sa.Column("signal_type", sa.String(), nullable=False, server_default="insight"),
    )
    op.add_column(
        "swarm_reflections",
        sa.Column("topic", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "swarm_reflections",
        sa.Column("match_key", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "swarm_reflections",
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "swarm_reflections",
        sa.Column("source_task_id", sa.String(), nullable=False, server_default=""),
    )

    op.create_index(op.f("ix_swarm_reflections_signal_type"), "swarm_reflections", ["signal_type"], unique=False)
    op.create_index(op.f("ix_swarm_reflections_topic"), "swarm_reflections", ["topic"], unique=False)
    op.create_index(op.f("ix_swarm_reflections_match_key"), "swarm_reflections", ["match_key"], unique=False)
    op.create_index(op.f("ix_swarm_reflections_source_task_id"), "swarm_reflections", ["source_task_id"], unique=False)

    op.alter_column("swarm_reflections", "signal_type", server_default=None)
    op.alter_column("swarm_reflections", "topic", server_default=None)
    op.alter_column("swarm_reflections", "match_key", server_default=None)
    op.alter_column("swarm_reflections", "tags", server_default=None)
    op.alter_column("swarm_reflections", "source_task_id", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_swarm_reflections_source_task_id"), table_name="swarm_reflections")
    op.drop_index(op.f("ix_swarm_reflections_match_key"), table_name="swarm_reflections")
    op.drop_index(op.f("ix_swarm_reflections_topic"), table_name="swarm_reflections")
    op.drop_index(op.f("ix_swarm_reflections_signal_type"), table_name="swarm_reflections")

    op.drop_column("swarm_reflections", "source_task_id")
    op.drop_column("swarm_reflections", "tags")
    op.drop_column("swarm_reflections", "match_key")
    op.drop_column("swarm_reflections", "topic")
    op.drop_column("swarm_reflections", "signal_type")
