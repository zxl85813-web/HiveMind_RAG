"""
Agent 基类 — 所有 Agent 的统一接口。

所有自定义 Agent 必须继承 BaseAgent 并实现:
    - invoke(message, context) → 处理请求
    - describe() → 描述自身能力 (供 Supervisor 路由)

参见: REGISTRY.md > 后端 > agents > BaseAgent
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger


class BaseAgent(ABC):
    """
    Agent 基类 — 蜂巢中所有 Agent 的统一接口。

    继承此类来创建新的 Agent:
        class RAGAgent(BaseAgent):
            name = "rag_agent"
            description = "Knowledge retrieval and augmented generation"

            async def invoke(self, message, context):
                # 你的 Agent 逻辑
                yield "response token"
    """

    name: str = "base_agent"
    description: str = "Base agent"
    model: str | None = None  # 偏好 LLM，None 则由路由器决定

    def __init__(self) -> None:
        logger.info(f"🐝 Agent initialized: {self.name}")

    @abstractmethod
    async def invoke(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        处理用户请求。

        Args:
            message: 用户输入
            context: 上下文 (conversation_id, kb_ids, history 等)

        Yields:
            响应 token (流式输出)
        """
        ...

    def describe(self) -> dict[str, str]:
        """描述自身能力 (供 Supervisor 路由决策)。"""
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model or "auto",
        }
