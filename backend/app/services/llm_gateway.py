"""
HiveMind LLM Gateway (M4.x)
Simplistic LLM router interface mapping requests to actual API calls.
"""

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings


class GatewayResponse:
    def __init__(self, content: str, metadata: dict):
        self.content = content
        self.metadata = metadata

class LLMGateway:
    async def call_tier(
        self,
        tier: int,
        prompt: str,
        system_prompt: str,
        response_format: dict | None = None
    ) -> GatewayResponse:

        # In a real app, tier determines the model.
        # Tier 3 = COMPLEX
        model = settings.ARK_MODEL
        api_key = settings.ARK_API_KEY or settings.LLM_API_KEY
        base_url = settings.ARK_BASE_URL or settings.LLM_BASE_URL

        if not api_key:
            logger.error("No LLM API Key configured.")
            if response_format and response_format.get("type") == "json_object":
                return GatewayResponse('{}', {})
            return GatewayResponse("Error: Missing API Key", {})

        logger.info(f"🚀 LLM Routing [Tier {tier}]: {model} via {base_url} (Key Masked: {api_key[:10]}...)")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                response_format=None,
                timeout=60.0
            )
            content = resp.choices[0].message.content or ""
            logger.debug(f"LLM Response [{model}]: {content[:200]}...")
            return GatewayResponse(content=content, metadata={"model": model, "tier": tier})
        except Exception as e:
            logger.error(f"LLM Gateway Exception: {e}")
            if response_format and response_format.get("type") == "json_object":
                # Fallback empty json if forced
                return GatewayResponse('{}', {})
            return GatewayResponse(f"Error calling LLM: {e}", {})

llm_gateway = LLMGateway()
