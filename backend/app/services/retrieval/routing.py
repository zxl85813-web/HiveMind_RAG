"""
Query Routing Step or Service.

Responsible for selecting the most appropriate Knowledge Base(s) for a given query,
based on the query intent and descriptions of available KBs.
"""

# ruff: noqa: W293

from sqlmodel import select

from app.core.database import async_session_factory
from app.core.logging import logger
from app.llm.router import LLMRouter
from app.models.knowledge import KnowledgeBase


class KnowledgeBaseSelector:
    """Selects the best knowledge bases for a query."""

    async def select_kbs(self, query: str, top_k: int = 1) -> list[KnowledgeBase]:
        """
        Dynamically selects the most relevant knowledge bases.
        For MVP, we just use an LLM or a simple heuristic if there aren't many.
        """

        # 1. Fetch available KBs
        async with async_session_factory() as session:
            all_kbs = (await session.exec(select(KnowledgeBase))).all()

        if not all_kbs:
            return []

        if len(all_kbs) == 1:
            return all_kbs

        # 2. Prepare descriptions for LLM routing
        kb_descriptions = "\n".join(
            [f"- ID: {kb.id} | Name: {kb.name} | Description: {kb.description or 'No description'}" for kb in all_kbs]
        )

        prompt = f"""
        You are an intelligent knowledge base router.
        Based on the user's query, select the MOST relevant knowledge base ID(s) from the following list.
        Only return the ID(s) on a single line, separated by commas.
        
        Available Knowledge Bases:
        {kb_descriptions}
        
        User Query: {query}
        
        Selected KB IDs:
        """

        try:
            router = LLMRouter()
            response = await router.acomplete(messages=[{"role": "user", "content": prompt}], temperature=0.0)

            if not response or not response.content:
                # Fallback to first if failed
                logger.warning("LLM Routing returned empty, falling back to all")
                return all_kbs

            selected_ids = [s.strip() for s in response.content.split(",")]
            selected_kbs = [kb for kb in all_kbs if kb.id in selected_ids]

            if not selected_kbs:
                return all_kbs

            return selected_kbs[:top_k]

        except Exception as e:
            logger.error(f"Error during KB routing: {e}")
            # Fallback to return all or first
            return all_kbs
