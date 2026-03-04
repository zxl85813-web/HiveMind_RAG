"""
Query Analytics and Pre-processing Step.

Handles intent expansion, normalization, and context enrichment based on memory.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.retrieval.protocol import RetrievalContext
from app.services.retrieval.steps import BaseRetrievalStep
from app.core.config import settings
from app.agents.llm_router import ModelTier

class QueryAnalysisResponse(BaseModel):
    intent: str = Field(description="The primary intent of the query (e.g., factual, summarization, analytical)")
    rewritten_query: str = Field(description="A single clear, unambiguous version of the user's query with resolved coreferences")
    hyde_document: Optional[str] = Field(default=None, description="A hypothetical, plausible answer document generated to aid semantic search")


class QueryPreProcessingStep(BaseRetrievalStep):
    """
    RAG Pre-processing:
    - Query Rewrite (Coreference Resolution based on dialogue history)
    - HyDE (Hypothetical Document Embeddings) Generation
    """
    
    def __init__(self, use_hyde: bool = True, rewrite_query: bool = True, decompose_query: bool = True):
        self.use_hyde = use_hyde
        self.rewrite_query = rewrite_query
        self.decompose_query = decompose_query

    async def execute(self, ctx: RetrievalContext):
        ctx.expanded_queries = [ctx.query]
        
        if self.rewrite_query:
            try:
                from app.agents.swarm import SwarmOrchestrator
                from langchain_core.messages import HumanMessage
                
                swarm = SwarmOrchestrator()
                llm = swarm.router.get_model(ModelTier.FAST)
                prompt = f"""
                You are a search query optimization assistant.
                
                User Query: {ctx.query}
                
                Your task is to:
                1. Resolve any pronouns (it, that, he, she) if context were provided (assume standalone for now, optimize for clarity).
                2. Expand acronyms or vague terms for better vector retrieval.
                3. Do NOT answer the question. Only return the rewritten search query.
                
                Rewritten Query:
                """
                
                resp = await llm.ainvoke([HumanMessage(content=prompt)])
                rewritten = resp.content.strip()
                
                if "\n" not in rewritten and len(rewritten) < 200:
                   if rewritten != ctx.query:
                       ctx.expanded_queries.append(rewritten)
                       ctx.log("QueryRewrite", f"Added rewritten: {rewritten}")
                
            except Exception as e:
                ctx.log("QueryRewrite", f"Rewrite failed: {e}")
        
        if self.use_hyde:
            try:
                from app.agents.swarm import SwarmOrchestrator
                from langchain_core.messages import HumanMessage
                
                swarm = SwarmOrchestrator()
                # HyDE needs a bit more thinking
                llm = swarm.router.get_model(ModelTier.STANDARD)
                
                prompt = f"""
                You are a hypothetical document generator.
                Please write a short, plausible (but maybe factually incorrect) paragraph that answers the following query.
                The goal is to use your generated text to search a vector database for similar real documents.
                
                Query: {ctx.query}
                
                Hypothetical Document:
                """
                
                resp = await llm.ainvoke([HumanMessage(content=prompt)])
                hyde_doc = resp.content.strip()
                if hyde_doc:
                    ctx.expanded_queries.append(hyde_doc)
                    ctx.log("HyDE", "Appended Hypothetical Document for Hybrid Search")
            except Exception as e:
                 ctx.log("HyDE", f"Failed: {e}")

        if self.decompose_query:
            try:
                from app.agents.swarm import SwarmOrchestrator
                from langchain_core.messages import HumanMessage
                
                swarm = SwarmOrchestrator()
                llm = swarm.router.get_model(ModelTier.FAST)
                prompt = f"""
                You are a search query decomposition engine.
                Is the following query complex enough to require being broken down into multiple independent, simpler sub-queries to retrieve all necessary information?
                
                Query: {ctx.query}
                
                If YES, provide up to 3 simpler, independent search queries, one per line. Do not number them.
                If NO (it's a simple query), just output exactly: NO_DECOMPOSITION
                """
                
                resp = await llm.ainvoke([HumanMessage(content=prompt)])
                content = resp.content.strip()
                
                if content != "NO_DECOMPOSITION":
                    sub_queries = [line.strip().lstrip('- ').strip() for line in content.split('\n') if line.strip()]
                    if sub_queries:
                        ctx.sub_queries = sub_queries
                        ctx.expanded_queries.extend(sub_queries)
                        ctx.log("QueryDecomp", f"Generated {len(sub_queries)} sub-queries: {sub_queries}")
            except Exception as e:
                ctx.log("QueryDecomp", f"Failed: {e}")
                 
                 
        if not ctx.expanded_queries:
            ctx.expanded_queries = [ctx.query]

        ctx.log("QueryProc", f"Prepared {len(ctx.expanded_queries)} queries for recall")
