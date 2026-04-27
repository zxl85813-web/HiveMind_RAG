"""
LLM Core Service — Wrapper for Model Inference (DeepSeek/SiliconFlow/OpenAI).
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.claw_router_governance import claw_router_governance
from app.services.dependency_circuit_breaker import breaker_manager
from app.services.fallback_orchestrator import fallback_orchestrator


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        self.model = settings.LLM_MODEL
        self._backup_client: AsyncOpenAI | None = None
        # print(f"🧠 LLM Service initialized with model: {self.model} at {settings.LLM_BASE_URL}")

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

    async def _route_model(self, messages: list[dict[str, str]]) -> str:
        """
        SG-006: multi-factor dynamic routing with cost guard.
        """
        decision = await claw_router_governance.decide(messages)
        logger.info(
            "[ClawRouter] tier={} model={} score={} reason={}",
            decision["tier"],
            decision["model"],
            decision["score"],
            decision["reason_code"],
        )
        return str(decision["model"])

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
        """
        try:
            target_model = await self._route_model(messages)
            # print(f"🚀 [Router] Selected model: {target_model}")

            async def _invoke():
                kwargs = {"model": target_model, "messages": messages, "temperature": temperature}
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                if extra_headers:
                    kwargs["extra_headers"] = extra_headers
                if extra_body:
                    kwargs["extra_body"] = extra_body
                return await self.client.chat.completions.create(**kwargs)

            response = await breaker_manager.execute("llm", _invoke)
            content = response.choices[0].message.content or ""
            return content
        except Exception as primary_error:
            logger.warning(f"[LLMService] primary invoke failed, trying fallback chain: {primary_error}")
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
        """
        try:
            target_model = await self._route_model(messages)

            async def _invoke_stream_create():
                return await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=target_model, messages=messages, temperature=temperature, stream=True
                    ),
                    timeout=30.0,  # 建立连接超时
                )

            stream = await breaker_manager.execute("llm", _invoke_stream_create)
            try:
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
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
