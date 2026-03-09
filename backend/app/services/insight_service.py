import json
import re

from pydantic import BaseModel

from app.core.llm import get_llm_service
from app.schemas.chat import AIAction


class SwarmInsight(BaseModel):
    summary: str
    thought: str
    actions: list[AIAction]


class InsightService:
    """
    Service to generate proactive strategic insights after a chat session.
    This is the core of the 'AI-First' philosophy: AI thinking ahead of the user.
    """

    @staticmethod
    def _clean_json_string(s: str) -> str:
        """Clean common LLM JSON artifacts like markdown blocks and trailing commas."""
        # 1. Strip markdown code blocks if present
        s = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", s, flags=re.DOTALL)

        # 2. Extract first { ... } block
        match = re.search(r"(\{.*\})", s, re.DOTALL)
        if not match:
            return s
        s = match.group(1)

        # 3. Handle common syntax issues like trailing commas before closing braces/brackets
        s = re.sub(r",\s*([\]\}])", r"\1", s)

        return s.strip()

    @staticmethod
    async def generate_session_insight(history: str, last_response: str) -> SwarmInsight | None:
        llm = get_llm_service()

        # Truncate safely
        history_trimmed = history[-2000:] if len(history) > 2000 else history
        response_trimmed = last_response[-1000:] if len(last_response) > 1000 else last_response

        prompt = f"""You are the 'Strategic Brain' of a RAG Platform. 
Analyze the recent chat session and provide a PROACTIVE NEXT STEP for the user.

Session History: {history_trimmed}
Last AI Response: {response_trimmed}

Available Action Types:
- "open_modal": Trigger a UI action (e.g., "create_kb")
- "navigate": Go to a specific page (e.g., "/evaluation", "/knowledge")
- "execute": Suggest a backend task
- "suggest": Suggest a follow-up question

IMPORTANT RULES:
- If the user mentions "上传" or "upload", provide action with target "/knowledge" and label "去上传文档"
- If the user mentions "创建知识库", provide action with type "open_modal" and target "create_kb", label "立刻创建"

Output ONLY valid JSON:
{{"summary": "brief summary", "thought": "reasoning", "actions": [{{"type": "navigate", "label": "Button Label", "target": "/path", "variant": "primary"}}]}}"""

        try:
            resp = await llm.chat_complete([{"role": "system", "content": prompt}], json_mode=True)

            cleaned_resp = InsightService._clean_json_string(resp)
            try:
                data = json.loads(cleaned_resp)
            except json.JSONDecodeError as e:
                print(f"Failed to parse cleaned JSON: {e}\nRaw: {resp[:200]}")
                # Last resort fuzzy extract
                json_match = re.search(r"(\{.*\})", resp, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                    except:
                        return None
                else:
                    return None

            return SwarmInsight(**data)
        except Exception as e:
            print(f"Failed to generate insight: {e}")
            return None
