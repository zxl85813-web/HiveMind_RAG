"""add_composite_performance_indexes

Fix-08: 添加复合索引以优化高频查询路径。

涉及表:
  - messages:                  (conversation_id, created_at)
  - knowledge_bases:           (owner_id, is_public)
  - document_chunks:           (document_id, chunk_index)
  - knowledge_base_documents:  (knowledge_base_id, status)
  - episodic_memories:         (user_id, created_at)
  - obs_swarm_traces:          (user_id, created_at)

Revision ID: a1b2c3d4e5f6
Revises: 2ab477643a2a, 5385c217a208
Create Date: 2026-04-27 12:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, tuple[str, ...], None] = ("2ab477643a2a", "5385c217a208")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── messages(conversation_id, created_at) ─────────────────────────────────
    # 优化场景: chat_stream 加载对话历史 ORDER BY created_at，
    #           get_conversations 批量查询最新消息
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )

    # ── knowledge_bases(owner_id, is_public) ──────────────────────────────────
    # 优化场景: list_kbs 按 owner_id 过滤 + is_public 条件，避免全表扫描
    op.create_index(
        "ix_knowledge_bases_owner_id_is_public",
        "knowledge_bases",
        ["owner_id", "is_public"],
        unique=False,
    )

    # ── document_chunks(document_id, chunk_index) ─────────────────────────────
    # 优化场景: 按文档顺序加载分块，chunk_index 排序查询
    op.create_index(
        "ix_document_chunks_document_id_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
        unique=False,
    )

    # ── knowledge_base_documents(knowledge_base_id, status) ───────────────────
    # 优化场景: 按 KB 筛选特定状态的文档（indexed / pending / failed）
    op.create_index(
        "ix_knowledge_base_documents_kb_id_status",
        "knowledge_base_documents",
        ["knowledge_base_id", "status"],
        unique=False,
    )

    # ── episodic_memories(user_id, created_at) ────────────────────────────────
    # 优化场景: 记忆蒸馏去重查询按用户 + 时间范围检索
    op.create_index(
        "ix_episodic_memories_user_id_created_at",
        "episodic_memories",
        ["user_id", "created_at"],
        unique=False,
    )

    # ── obs_swarm_traces(user_id, created_at) ─────────────────────────────────
    # 优化场景: 用户追踪历史查询，按时间倒序分页
    op.create_index(
        "ix_obs_swarm_traces_user_id_created_at",
        "obs_swarm_traces",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_obs_swarm_traces_user_id_created_at", table_name="obs_swarm_traces")
    op.drop_index("ix_episodic_memories_user_id_created_at", table_name="episodic_memories")
    op.drop_index("ix_knowledge_base_documents_kb_id_status", table_name="knowledge_base_documents")
    op.drop_index("ix_document_chunks_document_id_chunk_index", table_name="document_chunks")
    op.drop_index("ix_knowledge_bases_owner_id_is_public", table_name="knowledge_bases")
    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
