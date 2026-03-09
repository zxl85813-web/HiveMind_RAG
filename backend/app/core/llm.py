"""
LLM Core Service — Wrapper for Model Inference (DeepSeek/SiliconFlow/OpenAI).
"""
from openai import AsyncOpenAI
from app.core.config import settings
from typing import List, Dict, Any, AsyncGenerator
import json

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.LLM_MODEL
        # print(f"🧠 LLM Service initialized with model: {self.model} at {settings.LLM_BASE_URL}")

    def _route_model(self, messages: List[Dict[str, str]]) -> str:
        """
        Intelligence Router: Select model based on prompt content.
        - GLM-5: Complex reasoning, architecture, design, multi-role.
        - DeepSeek-V3: Coding, testing, general chat.
        """
        # Extract full text for keyword analysis
        full_text = " ".join([m.get("content", "").lower() for m in messages])
        
        # High-complexity keywords (Priority: GLM-5)
        reasoning_keywords = ["架构", "设计", "流程", "why", "reasoning", "swarm", "蜂群", "思维", "分析"]
        if any(kw in full_text for kw in reasoning_keywords):
            return settings.MODEL_GLM5
            
        # Coding/Standard keywords (Default: DeepSeek-V3)
        return settings.MODEL_DEEPSEEK_V3

    async def chat_complete(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        json_mode: bool = False,
        extra_headers: Dict[str, str] | None = None,
        extra_body: Dict[str, Any] | None = None
    ) -> str:
        """
        Non-streaming chat completion with intelligent routing.
        """
        try:
            target_model = self._route_model(messages)
            # print(f"🚀 [Router] Selected model: {target_model}")
            
            kwargs = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            if extra_headers:
                kwargs["extra_headers"] = extra_headers
            if extra_body:
                kwargs["extra_body"] = extra_body
                
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return str(e)

    async def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion with intelligent routing.
        """
        try:
            target_model = self._route_model(messages)
            
            stream = await self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            yield f"Error: {e}"

class MultimodalService(LLMService):
    def __init__(self):
        # Use Kimi Config for Multimodal
        api_key = settings.KIMI_API_KEY or settings.LLM_API_KEY
        base_url = settings.KIMI_BASE_URL 
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
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
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
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
