"""
Context Compactor v2.0 — intelligently manages long-context for HiveMind Agents.

Inspired by Claude Code's compact/prompt.ts:
- <analysis> 标签做 Chain-of-Thought (生成后自动删除, 提高总结质量)
- 结构化 9 段总结模板 (不遗漏关键信息)
- 增量 Compact (只压缩旧消息, 保留最近 N 条)
- 工具结果生命周期管理
"""

import asyncio
import re
from typing import Any, Awaitable, Callable

from langchain_core.messages import BaseMessage, SystemMessage
from loguru import logger

from app.core.token_service import TokenService

# ============================================================
#  Compact Prompt (借鉴 Claude Code compact/prompt.ts)
# ============================================================

COMPACT_PROMPT = """CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.

Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions.

Before providing your final summary, wrap your analysis in <analysis> tags to organize your thoughts:

1. Chronologically analyze each message. For each section identify:
   - The user's explicit requests and intents
   - Your approach to addressing the user's requests
   - Key decisions, technical concepts and code patterns
   - Specific details: file names, code snippets, function signatures, file edits
   - Errors encountered and how they were fixed
   - User feedback, especially corrections ("don't do X", "use Y instead")
2. Double-check for technical accuracy and completeness.

Your summary MUST include these sections:

1. **Primary Request and Intent**: All of the user's explicit requests in detail
2. **Key Technical Concepts**: Technologies, frameworks, and patterns discussed
3. **Files and Code Sections**: Files examined/modified/created, with code snippets and why each matters
4. **Errors and Fixes**: All errors encountered and how they were resolved
5. **User Feedback**: ALL user messages that are not tool results — these are critical for understanding changing intent
6. **Pending Tasks**: Any tasks explicitly asked for but not yet completed
7. **Current Work**: What was being worked on immediately before this summary, with file names and code snippets
8. **Memory Notes**: User preferences, corrections, or project context worth remembering across sessions
9. **Optional Next Step**: The next step directly in line with the user's most recent request. Include verbatim quotes showing where you left off.

<example>
<analysis>
[Your chronological analysis ensuring all points are covered]
</analysis>

<summary>
1. Primary Request and Intent:
   [Detailed description]

2. Key Technical Concepts:
   - [Concept 1]
   - [Concept 2]

3. Files and Code Sections:
   - `backend/app/main.py:42` — [Why this file matters] — [Code snippet]

4. Errors and Fixes:
   - [Error]: [How it was fixed]

5. User Feedback:
   - [Verbatim user message]

6. Pending Tasks:
   - [Task 1]

7. Current Work:
   [Precise description with file references]

8. Memory Notes:
   - [User preference or project context worth remembering]

9. Optional Next Step:
   [Next step with verbatim quote from conversation]
</summary>
</example>

REMINDER: Do NOT call any tools. Respond with plain text only — an <analysis> block followed by a <summary> block."""


def format_compact_summary(raw_summary: str) -> str:
    """
    Strip the <analysis> drafting scratchpad and extract the <summary>.

    The <analysis> block improves summary quality via Chain-of-Thought
    but has no informational value once the summary is written.
    (借鉴 Claude Code compact/prompt.ts formatCompactSummary)
    """
    # Strip analysis section
    result = re.sub(r"<analysis>[\s\S]*?</analysis>", "", raw_summary)

    # Extract summary content
    summary_match = re.search(r"<summary>([\s\S]*?)</summary>", result)
    if summary_match:
        content = summary_match.group(1).strip()
        result = f"Summary:\n{content}"
    else:
        # No tags found, use as-is
        result = result.strip()

    # Clean up extra whitespace
    result = re.sub(r"\n\n+", "\n\n", result)
    return result.strip()


class ContextCompactor:
    """
    Implements a robust history compaction strategy (v2.0).

    Strategy: [System] + [Turn 1 Anchor] + [Pinned] + [SUMMARY] + [Recent N turns]

    v2.0 improvements:
    - Structured 9-section compact prompt (Claude Code inspired)
    - <analysis> Chain-of-Thought for better summaries
    - Configurable recent message retention
    - Tool result lifecycle management
    """

    def __init__(
        self,
        llm: Any = None,
        threshold_tokens: int = 6400,
        keep_recent: int = 8,
    ):
        self.llm = llm
        self.threshold = threshold_tokens
        self.keep_recent = keep_recent

    async def _get_total_tokens(self, messages: list[BaseMessage]) -> int:
        """Utility to sum up tokens across all messages."""
        return TokenService.count_message_tokens(messages)

    async def compact_messages(
        self,
        messages: list[BaseMessage],
        pinned_messages: list[str] | None = None,
        on_compact_callback: Callable[[list[BaseMessage], str], Awaitable[None]] | None = None,
    ) -> list[BaseMessage]:
        """
        Processes a list of messages and returns a compacted version if needed.
        Compaction is triggered based on token budget.
        """
        current_tokens = await self._get_total_tokens(messages)

        if current_tokens <= self.threshold:
            return messages

        logger.info(
            f"🧬 [Compactor] Triggering compaction: {current_tokens} tokens > {self.threshold} threshold."
        )

        # 1. Split into segments
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # Need enough turns to maintain context quality
        min_messages = self.keep_recent + 4
        if len(other_msgs) < min_messages:
            return messages

        # Anchor: Turn 1 (First Human, First AI)
        anchors = other_msgs[:2]
        # Recent: Last N messages (preserving high resolution for current context)
        recent = other_msgs[-self.keep_recent :]
        # Middle: everything between anchors and recent
        middle = other_msgs[2 : -self.keep_recent]

        # Extract pinned messages from middle
        pinned_msgs_to_preserve = []
        if pinned_messages:
            new_middle = []
            for m in middle:
                if any(p in str(m.content) for p in pinned_messages):
                    pinned_msgs_to_preserve.append(m)
                    logger.debug(f"📌 [Compactor] Preserving pinned message: {str(m.content)[:40]}")
                else:
                    new_middle.append(m)
            middle = new_middle

        if not middle:
            return messages

        # 2. Summarize the middle segment
        summary_text = "History summary unavailable."
        if self.llm:
            summary_text = await self._summarize_segments(middle)
            compacted_msg = SystemMessage(
                content=(
                    f"[HISTORY_SUMMARY_BOUNDARY]\n"
                    f"This session is being continued from a previous conversation that ran out of context. "
                    f"The summary below covers turns 2 through {len(other_msgs) - self.keep_recent} "
                    f"({current_tokens} tokens compacted).\n\n"
                    f"{summary_text}\n"
                    f"[END_BOUNDARY]\n\n"
                    f"Recent messages are preserved verbatim. "
                    f"Continue from where you left off without asking the user any further questions."
                )
            )
        else:
            compacted_msg = SystemMessage(
                content=f"... [Compacted {len(middle)} messages to fit {self.threshold} token budget] ..."
            )

        # 3. Trigger episodic memory callback
        if on_compact_callback:
            try:
                asyncio.create_task(on_compact_callback(middle, summary_text))
            except Exception as e:
                logger.warning(f"Failed to trigger compaction callback: {e}")

        # 4. Rebuild: System + Anchors + Pinned + Summary + Recent
        rebuilt = system_msgs + anchors + pinned_msgs_to_preserve + [compacted_msg] + recent

        final_tokens = await self._get_total_tokens(rebuilt)
        logger.info(f"🧬 [Compactor] Final context size: {final_tokens} tokens (saved {current_tokens - final_tokens}).")

        return rebuilt

    async def _summarize_segments(self, segments: list[BaseMessage]) -> str:
        """
        Uses LLM to create a structured summary of historical segments.

        Uses the Claude Code-inspired compact prompt with <analysis> CoT.
        """
        # Truncate each message to prevent the summary request from overflowing
        history_text = "\n".join(
            [f"{type(m).__name__}: {str(m.content)[:500]}" for m in segments]
        )

        prompt = f"{COMPACT_PROMPT}\n\nHISTORY:\n{history_text}"

        try:
            response = await self.llm.ainvoke(prompt)
            raw = str(response.content)
            # Strip <analysis> block, keep only <summary>
            return format_compact_summary(raw)
        except Exception as e:
            logger.error(f"❌ Compaction summary failed: {e}")
            return "History summary unavailable."
