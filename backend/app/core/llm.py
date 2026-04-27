"""
LLM Core Service — Wrapper for Model Inference (DeepSeek/SiliconFlow/OpenAI).

v2.0 变更:
    - chat_complete() 从 API 响应中读取 prompt_cache_hit_tokens，
      传入 TokenTracker.calculate_cost() 计算准确成本（区分 cache hit/miss 费率）。
    - 每次调用后 fire-and-forget 写入 LLMMetric，包含 tokens_cache_hit 和
      cache_savings_usd，供 BudgetService 展示真实节省。
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.llm.tracker import TokenTracker
from app.services.claw_router_governance import claw_router_governance
from app.services.dependency_circuit_breaker import breaker_manager
from app.services.fallback_orchestrator import fallback_orchestrator


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        self.model = settings.LLM_MODEL
        self._backup_client: AsyncOpenAI | None = None
        # NVIDIA NIM client — lazy init, used for reasoning tier
        self._nvidia_client: AsyncOpenAI | None = None
        # print(f"🧠 LLM Service initialized with model: {self.model} at {settings.LLM_BASE_URL}")

    def _get_nvidia_client(self) -> AsyncOpenAI | None:
        """
        Return a lazily-initialised AsyncOpenAI client pointed at NVIDIA NIM.
        Returns None when NVIDIA_API_KEY is not configured.
        """
        if not settings.NVIDIA_API_KEY:
            return None
        if self._nvidia_client is None:
            self._nvidia_client = AsyncOpenAI(
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
            )
            logger.info(
                "[LLMService] NVIDIA NIM client initialised — model={} base_url={}",
                settings.NVIDIA_REASONING_MODEL,
                settings.NVIDIA_BASE_URL,
            )
        return self._nvidia_client

    def _extract_query(self, messages: list[dict[str, str]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                return msg["content"]
        return " ".join([m.get("content", "") for m in messages]).strip()

    async def _invoke_completion(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        json_mode: bool,
        extra_headers: dict[str, str] | None,
        extra_body: dict[str, Any] | None,
    ) -> str:
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if extra_headers:
            kwargs["extra_headers"] = extra_headers
        if extra_body:
            kwargs["extra_body"] = extra_body
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def _get_backup_client(self) -> AsyncOpenAI | None:
        if not settings.OPENAI_API_KEY:
            return None
        if self._backup_client is None:
            self._backup_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
        return self._backup_client

    async def _recover_non_stream(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        json_mode: bool,
        extra_headers: dict[str, str] | None,
        extra_body: dict[str, Any] | None,
    ) -> str:
        query = self._extract_query(messages)

        async def _local_invoke() -> str:
            return await self._invoke_completion(
                client=self.client,
                model=settings.DEFAULT_SIMPLE_MODEL,
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
                extra_headers=extra_headers,
                extra_body=extra_body,
            )

        backup_client = self._get_backup_client()
        backup_model = settings.DEFAULT_SIMPLE_MODEL

        async def _backup_invoke() -> str:
            if backup_client is None:
                raise RuntimeError("Backup provider not configured")
            return await self._invoke_completion(
                client=backup_client,
                model=backup_model,
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
                extra_headers=extra_headers,
                extra_body=extra_body,
            )

        recovered, reason_code = await fallback_orchestrator.recover_text(
            query=query,
            local_invoke=_local_invoke,
            backup_invoke=_backup_invoke if backup_client is not None else None,
        )
        logger.warning(f"[LLMService] fallback activated: {reason_code}")
        return recovered

    async def _route_model(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        """
        SG-006: multi-factor dynamic routing with cost guard.

        Returns
        -------
        (model_name, tier)  — tier is used downstream to pick the right client.
        """
        decision = await claw_router_governance.decide(messages)
        logger.info(
            "[ClawRouter] tier={} model={} score={} reason={}",
            decision["tier"],
            decision["model"],
            decision["score"],
            decision["reason_code"],
        )
        return str(decision["model"]), decision["tier"]

    def _client_for_tier(self, tier: str) -> AsyncOpenAI:
        """
        Select the appropriate AsyncOpenAI client based on routing tier.

        Reasoning tier → NVIDIA NIM (DeepSeek-V4-Pro, free account).
        All other tiers → primary SiliconFlow/Ark client.
        """
        if tier == "reasoning":
            nvidia = self._get_nvidia_client()
            if nvidia is not None:
                logger.info("[LLMService] 🟢 NVIDIA NIM selected for reasoning tier")
                return nvidia
            logger.warning("[LLMService] NVIDIA_API_KEY not set — falling back to primary client for reasoning tier")
        return self.client

    def _extract_cache_hit_tokens(self, response: Any) -> int:
        """
        从 API 响应中提取前缀缓存命中的 token 数。

        DeepSeek V4 / OpenAI 在 usage 对象中返回:
          - prompt_cache_hit_tokens  (DeepSeek 官方 API)
          - prompt_tokens_details.cached_tokens  (OpenAI 格式)
        两种格式都兼容。
        """
        try:
            usage = getattr(response, "usage", None)
            if usage is None:
                return 0
            # DeepSeek 格式
            hit = getattr(usage, "prompt_cache_hit_tokens", None)
            if hit is not None:
                return int(hit)
            # OpenAI 格式
            details = getattr(usage, "prompt_tokens_details", None)
            if details is not None:
                cached = getattr(details, "cached_tokens", None)
                if cached is not None:
                    return int(cached)
        except Exception:
            pass
        return 0

    def _record_metric_bg(
        self,
        *,
        model_name: str,
        provider: str,
        latency_ms: float,
        tokens_input: int,
        tokens_output: int,
        tokens_cache_hit: int,
        is_error: bool = False,
        error_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Fire-and-forget: 计算成本后写入 LLMMetric。"""
        cost = TokenTracker.calculate_cost(
            prompt_tokens=tokens_input,
            completion_tokens=tokens_output,
            model=model_name,
            cache_hit_tokens=tokens_cache_hit,
        )
        savings = TokenTracker.estimate_cache_savings(
            prompt_tokens=tokens_input,
            cache_hit_tokens=tokens_cache_hit,
            model=model_name,
        )
        if tokens_cache_hit > 0:
            logger.info(
                "[LLMService] 💰 cache hit={}/{} tokens | saved=${:.6f} | cost=${:.6f}",
                tokens_cache_hit, tokens_input, savings, cost,
            )

        from app.services.observability_service import record_llm_metric
        import asyncio as _asyncio

        async def _write():
            await record_llm_metric(
                model_name=model_name,
                provider=provider,
                latency_ms=latency_ms,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_cache_hit=tokens_cache_hit,
                cost=cost,
                cache_savings_usd=savings,
                is_error=is_error,
                error_type=error_type,
                context=context,
            )

        try:
            loop = _asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_write())
        except Exception as exc:
            logger.debug(f"[LLMService] metric write skipped: {exc}")

    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        json_mode: bool = False,
        extra_headers: dict[str, str] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        """
        Non-streaming chat completion with intelligent routing.

        Reasoning tier automatically uses NVIDIA NIM (DeepSeek-V4-Pro) when
        NVIDIA_API_KEY is configured; all other tiers use the primary client.

        v2.0: 从响应 usage 中读取 prompt_cache_hit_tokens，用于准确计费和
        cache savings 统计。
        """
        t0 = time.monotonic()
        target_model = self.model
        tier = "balanced"
        try:
            target_model, tier = await self._route_model(messages)
            active_client = self._client_for_tier(tier)

            # For NVIDIA reasoning tier, inject thinking mode via extra_body
            if tier == "reasoning" and active_client is self._nvidia_client:
                extra_body = {
                    **(extra_body or {}),
                    "chat_template_kwargs": {
                        "thinking": settings.NVIDIA_THINKING_ENABLED,
                        "reasoning_effort": settings.NVIDIA_REASONING_EFFORT,
                    },
                }
                # NVIDIA NIM reasoning model overrides the ClawRouter model name
                target_model = settings.NVIDIA_REASONING_MODEL
                logger.info(
                    "[LLMService] 🧠 NVIDIA NIM reasoning — model={} thinking={} effort={}",
                    target_model,
                    settings.NVIDIA_THINKING_ENABLED,
                    settings.NVIDIA_REASONING_EFFORT,
                )

            async def _invoke():
                kwargs: dict[str, Any] = {"model": target_model, "messages": messages, "temperature": temperature}
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                if extra_headers:
                    kwargs["extra_headers"] = extra_headers
                if extra_body:
                    kwargs["extra_body"] = extra_body
                return await active_client.chat.completions.create(**kwargs)

            response = await breaker_manager.execute("llm", _invoke)
            content = response.choices[0].message.content or ""

            # ── 成本计量 (v2.0) ──────────────────────────────────────────
            latency_ms = (time.monotonic() - t0) * 1000
            usage = getattr(response, "usage", None)
            tokens_input = getattr(usage, "prompt_tokens", 0) if usage else 0
            tokens_output = getattr(usage, "completion_tokens", 0) if usage else 0
            tokens_cache_hit = self._extract_cache_hit_tokens(response)
            self._record_metric_bg(
                model_name=target_model,
                provider=settings.LLM_PROVIDER,
                latency_ms=latency_ms,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_cache_hit=tokens_cache_hit,
                context={"tier": tier},
            )
            return content
        except Exception as primary_error:
            logger.warning(f"[LLMService] primary invoke failed, trying fallback chain: {primary_error}")
            self._record_metric_bg(
                model_name=target_model,
                provider=settings.LLM_PROVIDER,
                latency_ms=(time.monotonic() - t0) * 1000,
                tokens_input=0,
                tokens_output=0,
                tokens_cache_hit=0,
                is_error=True,
                error_type=type(primary_error).__name__,
                context={"tier": tier},
            )
            try:
                return await self._recover_non_stream(
                    messages=messages,
                    temperature=temperature,
                    json_mode=json_mode,
                    extra_headers=extra_headers,
                    extra_body=extra_body,
                )
            except Exception as fallback_error:
                logger.error(f"[LLMService] fallback chain exhausted: {fallback_error}")
                raise RuntimeError(
                    f"LLM unavailable: {primary_error}"
                ) from fallback_error

    async def stream_chat(self, messages: list[dict[str, str]], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion with intelligent routing.

        Reasoning tier uses NVIDIA NIM when configured; other tiers use the
        primary client.  NVIDIA NIM streaming strips reasoning_content tokens
        and only yields the final answer content.
        """
        try:
            target_model, tier = await self._route_model(messages)
            active_client = self._client_for_tier(tier)
            stream_extra_body: dict[str, Any] | None = None

            if tier == "reasoning" and active_client is self._nvidia_client:
                target_model = settings.NVIDIA_REASONING_MODEL
                stream_extra_body = {
                    "chat_template_kwargs": {
                        "thinking": settings.NVIDIA_THINKING_ENABLED,
                        "reasoning_effort": settings.NVIDIA_REASONING_EFFORT,
                    }
                }
                logger.info(
                    "[LLMService] 🧠 NVIDIA NIM streaming — model={} effort={}",
                    target_model,
                    settings.NVIDIA_REASONING_EFFORT,
                )

            async def _invoke_stream_create():
                kwargs: dict[str, Any] = {
                    "model": target_model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                }
                if stream_extra_body:
                    kwargs["extra_body"] = stream_extra_body
                return await asyncio.wait_for(
                    active_client.chat.completions.create(**kwargs),
                    timeout=30.0,  # 建立连接超时
                )

            stream = await breaker_manager.execute("llm", _invoke_stream_create)
            try:
                async for chunk in stream:
                    if not getattr(chunk, "choices", None):
                        continue
                    delta = chunk.choices[0].delta
                    # Skip NVIDIA reasoning/thinking tokens — only yield final answer
                    if getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None):
                        continue
                    content = delta.content
                    if content:
                        yield content
            except TimeoutError:
                logger.warning("[LLMService] stream chunk timeout, activating fallback")
                raise
        except Exception as primary_error:
            logger.warning(f"[LLMService] stream primary failed, trying fallback chain: {primary_error}")
            try:
                recovered = await asyncio.wait_for(
                    self._recover_non_stream(
                        messages=messages,
                        temperature=temperature,
                        json_mode=False,
                        extra_headers=None,
                        extra_body=None,
                    ),
                    timeout=60.0,  # fallback 总超时
                )
                for i in range(0, len(recovered), 80):
                    chunk = recovered[i : i + 80]
                    if chunk:
                        yield chunk
            except Exception as fallback_error:
                yield f"Error: {primary_error}; fallback failed: {fallback_error}"


class MultimodalService(LLMService):
    def __init__(self):
        # Use Kimi Config for Multimodal
        api_key = settings.KIMI_API_KEY or settings.LLM_API_KEY
        base_url = settings.KIMI_BASE_URL

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = settings.KIMI_MODEL

    async def analyze_image(self, image_url: str, prompt: str = "Describe this image detailedly.") -> str:
        """
        Analyze an image using Multimodal Model (e.g. Kimi k2.5).
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ]
            response = await self.client.chat.completions.create(model=self.model, messages=messages)
            return response.choices[0].message.content
        except Exception as e:
            print(f"👁️ Multimodal Error: {e}")
            return f"Error analyzing image: {e}"


_llm_service = None
_mm_service = None


def get_llm_service():
    global _llm_service
    if not _llm_service:
        _llm_service = LLMService()
    return _llm_service


def get_multimodal_service():
    global _mm_service
    if not _mm_service:
        _mm_service = MultimodalService()
    return _mm_service
