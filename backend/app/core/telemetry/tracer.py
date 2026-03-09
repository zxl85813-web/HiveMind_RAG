"""
Lightweight Redis-buffered Telemetry Tracer.

This provides an `AsyncCallbackHandler` that captures LLM and Agent Tool interactions
and buffers them perfectly into a Redis list without blocking the execution thread.
These logs are later collected by a background worker (or Celery) to insert into
the PostgreSQL `obs_agent_spans` table.
"""

import json
import logging
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.config import settings
from app.models.observability import SpanType

logger = logging.getLogger(__name__)


class LightweightRedisTracer(AsyncCallbackHandler):
    """
    An async callback handler that logs Langchain events to Redis for high-throughput
    tracing without HTTP overhead (unlike Langfuse).
    """

    def __init__(self, trace_id: str, agent_name: str):
        super().__init__()
        self.trace_id = trace_id
        self.agent_name = agent_name
        # Connect to Redis. In a production app you'd reuse a global connection pool.
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def _push_span(self, span_data: dict[str, Any]) -> None:
        """Push a span dictionary to the Redis list buffer."""
        try:
            await self.redis.lpush("trace_span_buffer", json.dumps(span_data, ensure_ascii=False))
        except Exception as e:
            # We must never crash the main application thread due to telemetry failure
            logger.error(f"Failed to push trace info to Redis: {e}")

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        pass  # We capture everything needed at on_llm_end

    async def on_llm_end(
        self, response: LLMResult, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        """Log completing an LLM generation with tokens used."""
        try:
            tokens = 0
            if response.llm_output and "token_usage" in response.llm_output:
                tokens = response.llm_output["token_usage"].get("total_tokens", 0)

            text_outputs = []
            for gen_list in response.generations:
                for gen in gen_list:
                    # Capture up to 500 chars to avoid payload bloat
                    text_outputs.append(gen.text[:500])

            span_data = {
                "trace_id": self.trace_id,
                "agent_name": self.agent_name,
                "action_type": SpanType.LLM_CALL.value,
                "payload": {"outputs": text_outputs},
                "tokens": tokens,
                "is_error": False,
            }
            await self._push_span(span_data)
        except Exception as e:
            logger.error(f"Error extracting LLM trace: {e}")

    async def on_llm_error(
        self, error: Exception | KeyboardInterrupt, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        span_data = {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "action_type": SpanType.LLM_CALL.value,
            "payload": {"error": str(error)},
            "tokens": 0,
            "is_error": True,
        }
        await self._push_span(span_data)

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        pass

    async def on_tool_end(self, output: str, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> None:
        tool_name = kwargs.get("name", "unknown_tool")

        span_data = {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "action_type": SpanType.TOOL_INVOKE.value,
            "payload": {"tool": tool_name, "output_preview": output[:500]},
            "tokens": 0,
            "is_error": False,
        }
        await self._push_span(span_data)

    async def on_tool_error(
        self, error: Exception | KeyboardInterrupt, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        tool_name = kwargs.get("name", "unknown_tool")

        span_data = {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "action_type": SpanType.TOOL_INVOKE.value,
            "payload": {"tool": tool_name, "error": str(error)},
            "tokens": 0,
            "is_error": True,
        }
        await self._push_span(span_data)
