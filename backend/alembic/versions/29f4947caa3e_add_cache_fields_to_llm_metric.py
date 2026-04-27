"""add_cache_fields_to_llm_metric

Adds tokens_cache_hit and cache_savings_usd to obs_llm_metrics to support
DeepSeek V4 prefix-cache cost tracking.

Revision ID: 29f4947caa3e
Revises: b2c3d4e5f6a7
Create Date: 2026-04-27 08:24:54.118548

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '29f4947caa3e'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tokens_cache_hit: input tokens served from prefix cache (DeepSeek V4 / OpenAI)
    op.add_column(
        'obs_llm_metrics',
        sa.Column('tokens_cache_hit', sa.Integer(), nullable=False, server_default='0'),
    )
    # cache_savings_usd: USD saved vs. full cache-miss billing
    op.add_column(
        'obs_llm_metrics',
        sa.Column('cache_savings_usd', sa.Float(), nullable=False, server_default='0.0'),
    )


def downgrade() -> None:
    op.drop_column('obs_llm_metrics', 'cache_savings_usd')
    op.drop_column('obs_llm_metrics', 'tokens_cache_hit')
