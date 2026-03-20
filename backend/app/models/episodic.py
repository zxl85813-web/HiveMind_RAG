"""
Database models for Episodic Memory (Cross-session Summaries).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlmodel import JSON, Field, SQLModel


class EpisodicMemory(SQLModel, table=True):
    """
    情节记忆：跨会话的对话摘要存储单元。

    每条记录代表一次完整对话的蒸馏结果，
    包含结构化的摘要、关键词和可查询的元数据。
    """

    __tablename__ = "episodic_memories"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # ── 归属维度 ──────────────────────────────
    user_id: str = Field(index=True, description="用户 ID，记忆隔离单元")
    conversation_id: str = Field(index=True, description="来源会话 ID")
    agent_names: list[str] = Field(
        default_factory=list,
        sa_type=JSON,
        description="参与本次会话的 Agent 列表",
    )

    # ── 核心内容 ──────────────────────────────
    summary: str = Field(description="会话级别的结构化摘要（LLM 生成）")
    key_decisions: list[str] = Field(
        default_factory=list,
        sa_type=JSON,
        description="本次会话中产生的关键决策点",
    )
    topics: list[str] = Field(
        default_factory=list,
        sa_type=JSON,
        description="会话主题关键词（用于快速路由）",
    )
    user_intent: str = Field(default="", description="用户的核心意图（一句话）")

    # ── 质量与价值度量 ────────────────────────
    message_count: int = Field(default=0, description="原始消息轮数")
    topic_coverage: float = Field(default=0.5, description="话题覆盖密度（0-1），越高代表内容越丰富")
    chroma_doc_id: str | None = Field(default=None, description="在 ChromaDB episodic_episodes 集合中的文档 ID（用于向量召回）")

    # ── 记忆温度（继承 Tier-1 的衰减机制）────
    temperature: float = Field(default=1.0, description="记忆热度（0-1），被召回时升温，每日按系数衰减")
    recall_count: int = Field(default=0, description="被召回次数")
    last_recalled_at: datetime | None = Field(default=None)

    # ── 时间戳 ───────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    conversation_started_at: datetime | None = Field(default=None)
    conversation_ended_at: datetime | None = Field(default=None)

    # ── 扩展字段 ─────────────────────────────
    extra: dict[str, Any] = Field(default_factory=dict, sa_type=JSON, description="预留扩展字段，存储任意附加元数据")
