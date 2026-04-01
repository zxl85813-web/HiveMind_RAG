"""
Context Compactor — intelligently manages long-context for HiveMind Agents.
Inspired by Claude Code's history compaction logic.
"""

import asyncio
from typing import Any, Callable, Awaitable

from langchain_core.messages import BaseMessage, SystemMessage
from loguru import logger


class ContextCompactor:
    """
    Implements a robust history truncation and summarization strategy.
    
    Strategy: [System] + [Turn 1] + [SUMMARY OF MIDDLE] + [Recent 10 turns]
    """

    def __init__(self, llm: Any = None, threshold_messages: int = 20):
        self.llm = llm # LLM used for summarization
        self.threshold = threshold_messages

    async def compact_messages(
        self,
        messages: list[BaseMessage],
        on_compact_callback: Callable[[list[BaseMessage], str], Awaitable[None]] | None = None
    ) -> list[BaseMessage]:
        """
        Processes a list of messages and returns a compacted version if needed.
        """
        if len(messages) <= self.threshold:
            return messages

        logger.info(f"🧬 [Compactor] Triggering compaction for {len(messages)} messages.")

        # 1. Split into segments
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        if len(other_msgs) < 15:
            return messages

        # Anchor: Turn 1 (First Human, First AI)
        anchors = other_msgs[:2]
        # Recent: Last 10 messages (preserving high resolution for current context)
        recent = other_msgs[-10:]
        # Middle: Everything else
        middle = other_msgs[2:-10]

        if not middle:
            return messages

        # 2. Summarize the middle segment (If LLM is provided)
        summary_text = "History summary unavailable."
        if self.llm:
            summary_text = await self._summarize_segments(middle)
            compacted_msg = SystemMessage(content=f"""
[HISTORY_SUMMARY_BOUNDARY]
The middle part (Turn 2 to Turn {len(other_msgs)-10}) has been compacted. 
Summary of developments:
{summary_text}
[END_BOUNDARY]
""")
        else:
            compacted_msg = SystemMessage(content=f"... [Compacted {len(middle)} messages for context optimization] ...")

        # 🛠️ Trigger Episodic Memory (Phase 2 integration)
        if on_compact_callback:
            try:
                # Fire and forget callback (usually a background task in Swarm)
                asyncio.create_task(on_compact_callback(middle, summary_text))
            except Exception as e:
                logger.warning(f"Failed to trigger compaction callback: {e}")

        # 3. Rebuild (System + Anchors + Summary + Recent)
        return system_msgs + anchors + [compacted_msg] + recent

    async def _summarize_segments(self, segments: list[BaseMessage]) -> str:
        """Uses LLM to create a concise summary of historical segments."""
        history_text = "\n".join([f"{type(m).__name__}: {m.content[:200]}" for m in segments])

        prompt = f"""
Summarize the following agent conversation history concisely. 
Focus ONLY on key decisions, tool output data, and user preferences discovered.
Exclude thinking logs or intermediate chatter.

HISTORY:
{history_text}

CONCISE SUMMARY:"""

        try:
            response = await self.llm.ainvoke(prompt)
            return str(response.content)
        except Exception as e:
            logger.error(f"❌ Compaction summary failed: {e}")
            return "History summary unavailable."
