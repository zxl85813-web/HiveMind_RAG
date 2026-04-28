"""add_cache_fields_to_llm_metric

Creates obs_llm_metrics table if missing (was never given a create_table
migration), then adds tokens_cache_hit and cache_savings_usd columns to
support DeepSeek V4 prefix-cache cost tracking.

Revision ID: 29f4947caa3e
Revises: b2c3d4e5f6a7
Create Date: 2026-04-27 08:24:54.118548

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = '29f4947caa3e'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = 'obs_llm_metrics'


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa_inspect(conn)

    if TABLE_NAME not in inspector.get_table_names():
        # Table was never created by any prior migration — create it now.
        op.create_table(
            TABLE_NAME,
            sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('tokens_input', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('tokens_output', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('tokens_cache_hit', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('cost', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('cache_savings_usd', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('is_error', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('error_type', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('context', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_obs_llm_metrics_model_name', TABLE_NAME, ['model_name'])
        op.create_index('ix_obs_llm_metrics_provider', TABLE_NAME, ['provider'])
        op.create_index('ix_obs_llm_metrics_is_error', TABLE_NAME, ['is_error'])
        op.create_index('ix_obs_llm_metrics_created_at', TABLE_NAME, ['created_at'])
    else:
        # Table exists (e.g. from create_all in dev) — just add the new columns.
        existing_columns = {c['name'] for c in inspector.get_columns(TABLE_NAME)}

        if 'tokens_cache_hit' not in existing_columns:
            op.add_column(
                TABLE_NAME,
                sa.Column('tokens_cache_hit', sa.Integer(), nullable=False, server_default='0'),
            )
        if 'cache_savings_usd' not in existing_columns:
            op.add_column(
                TABLE_NAME,
                sa.Column('cache_savings_usd', sa.Float(), nullable=False, server_default='0.0'),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa_inspect(conn)

    if TABLE_NAME in inspector.get_table_names():
        existing_columns = {c['name'] for c in inspector.get_columns(TABLE_NAME)}
        if 'cache_savings_usd' in existing_columns:
            op.drop_column(TABLE_NAME, 'cache_savings_usd')
        if 'tokens_cache_hit' in existing_columns:
            op.drop_column(TABLE_NAME, 'tokens_cache_hit')
