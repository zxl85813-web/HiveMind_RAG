"""
Context Compactor — intelligently manages long-context for HiveMind Agents.
Inspired by Claude Code's history compaction logic.
"""

import asyncio
from typing import Any, Callable, Awaitable

from langchain_core.messages import BaseMessage, SystemMessage
from loguru import logger

from app.core.token_service import TokenService


class ContextCompactor:
    """
    Implements a robust history truncation and summarization strategy.
    
    Strategy: [System] + [Turn 1] + [SUMMARY OF MIDDLE] + [Recent 10 turns]
    """

    def __init__(self, llm: Any = None, threshold_tokens: int = 6400):
        self.llm = llm # LLM used for summarization
        self.threshold = threshold_tokens

    async def _get_total_tokens(self, messages: list[BaseMessage]) -> int:
        """Utility to sum up tokens across all messages."""
        return TokenService.count_message_tokens(messages)

    async def compact_messages(
        self,
        messages: list[BaseMessage],
        on_compact_callback: Callable[[list[BaseMessage], str], Awaitable[None]] | None = None
    ) -> list[BaseMessage]:
        """
        Processes a list of messages and returns a compacted version if needed.
        Compaction is triggered based on token budget, not just message count (P0 Hardening).
        """
        current_tokens = await self._get_total_tokens(messages)
        
        if current_tokens <= self.threshold:
            return messages

        logger.info(f"🧬 [Compactor] Triggering compaction: {current_tokens} tokens > {self.threshold} threshold.")

        # 1. Split into segments
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # We need at least some turns to maintain context quality after anchor
        if len(other_msgs) < 12:
            return messages

        # Anchor: Turn 1 (First Human, First AI)
        anchors = other_msgs[:2]
        # Recent: Last 8 messages (preserving high resolution for current context)
        recent = other_msgs[-8:]
        # Middle: Everything else
        middle = other_msgs[2:-8]

        if not middle:
            return messages

        # 2. Summarize the middle segment (If LLM is provided)
        summary_text = "History summary unavailable."
        if self.llm:
            summary_text = await self._summarize_segments(middle)
            compacted_msg = SystemMessage(content=f"""
[HISTORY_SUMMARY_BOUNDARY]
The middle part (Turn 2 to Turn {len(other_msgs)-8}) has been compacted to save tokens ({current_tokens} -> COMPACTED). 
Summary of developments:
{summary_text}
[END_BOUNDARY]
""")
        else:
            compacted_msg = SystemMessage(content=f"... [Compacted {len(middle)} messages to fit {self.threshold} token budget] ...")

        # 🛠️ Trigger Episodic Memory (Phase 2 integration)
        if on_compact_callback:
            # Fire and forget callback
            try:
                asyncio.create_task(on_compact_callback(middle, summary_text))
            except Exception as e:
                logger.warning(f"Failed to trigger compaction callback: {e}")

        # 3. Rebuild (System + Anchors + Summary + Recent)
        rebuilt = system_msgs + anchors + [compacted_msg] + recent
        
        # Double check if we are STILL over budget (shouldn't be, but good safe-guard)
        final_tokens = await self._get_total_tokens(rebuilt)
        logger.info(f"🧬 [Compactor] Final context size: {final_tokens} tokens.")
        
        return rebuilt

    async def _summarize_segments(self, segments: list[BaseMessage]) -> str:
        """Uses LLM to create a concise summary of historical segments."""
        # Truncate each snippet so the summary request doesn't overflow itself
        history_text = "\n".join([f"{type(m).__name__}: {str(m.content)[:500]}" for m in segments])

        prompt = f"""
Summarize the following agent conversation history concisely. 
Focus ONLY on key decisions, tool output data, and user preferences discovered.
Exclude thinking logs or intermediate chatter.

HISTORY:
{history_text}

CONCISE SUMMARY (MARKDOWN):"""

        try:
            response = await self.llm.ainvoke(prompt)
            return str(response.content)
        except Exception as e:
            logger.error(f"❌ Compaction summary failed: {e}")
            return "History summary unavailable."
