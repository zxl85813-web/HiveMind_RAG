
import json
from typing import Any, List, Optional
from loguru import logger
from app.sdk.core.graph_store import get_graph_store
from pydantic import BaseModel

class SocializedConsensus(BaseModel):
    decision_point: str
    consensus_summary: str
    rationale: str
    tags: List[str] = []
    trace_id: str

class SocialGraphService:
    """
    L5 Strategy: Implements the 'Collective Unconscious' by persisting and 
    recalling swarm decision patterns in Neo4j.
    """
    def __init__(self):
        self.store = get_graph_store()
        self.cache_path = "storage/social_wisdom_cache.json"
        self._ensure_cache()

    def _ensure_cache(self):
        import os
        os.makedirs("storage", exist_ok=True)
        if not os.path.exists(self.cache_path):
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump([], f)

    async def solidify_consensus(self, consensus: SocializedConsensus):
        """
        Embeds a swarm consensus into the global architecture graph (and local cache).
        """
        logger.info(f"🕸️ [SocialGraph] Solidifying consensus for: {consensus.decision_point[:50]}...")
        
        # 1. Neo4j Attempt
        query = (
            "MERGE (d:DecisionPoint {query: $query}) "
            "ON CREATE SET d.created_at = timestamp() "
            "MERGE (c:Consensus {summary: $summary}) "
            "ON CREATE SET c.rationale = $rationale, c.trace_id = $trace_id, c.created_at = timestamp() "
            "MERGE (d)-[r:HAS_CONSENSUS]->(c) "
            "SET r.updated_at = timestamp()"
        )
        params = consensus.dict()
        params["query"] = params.pop("decision_point")
        params["summary"] = params.pop("consensus_summary")
        await self.store.execute_query(query, params)
        
        # 2. Local Cache (L5 Resilience Layer)
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            cache.append(consensus.dict())
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update local wisdom cache: {e}")
            
        logger.info("🕸️ [SocialGraph] Consensus solidified successfully.")

    async def suggest_prior_wisdom(self, query: str) -> List[dict]:
        """
        Recalls past consensus that might be relevant to the current query.
        Uses a combination of keyword matching and graph neighborhood exploration.
        """
        logger.info(f"🧠 [Subconscious] Scanning collective图谱 for: {query}")
        
        search_query = (
            "MATCH (d:DecisionPoint)-[:HAS_CONSENSUS]->(c:Consensus) "
            "WHERE d.query CONTAINS $keyword OR c.summary CONTAINS $keyword "
            "RETURN d.query as point, c.summary as solution, c.rationale as rationale "
            "LIMIT 3"
        )

        # 🚀 L5 Strategic Improvement: Smart keywords extraction
        stop_words = {'how', 'should', 'the', 'what', 'can', 'I', 'my', 'in', 'of', 'and', 'for', 'with', 'to'}
        extracted_keywords = [
            k.lower() for k in query.replace('?', '').split() 
            if len(k) > 3 and k.lower() not in stop_words
        ]
        
        # Priority on longest/most specific technical terms
        extracted_keywords.sort(key=len, reverse=True)
        keywords = extracted_keywords[:3] # Use top 3 specific terms
        
        results = []
        seen_solutions = set()
        
        for kw in keywords:
            batch = await self.store.execute_query(search_query, {"keyword": kw})
            for r in batch:
                if r['solution'] not in seen_solutions:
                    results.append(r)
                    seen_solutions.add(r['solution'])
        
        # 🧠 L5 Intelligence Fallback: Semantic Association
        if not results:
            logger.info("🕵️ [Subconscious] Keywords failed. Attempting Semantic Association...")
            # 1. Try Neo4j first
            all_points = await self.store.execute_query("MATCH (d:DecisionPoint)-[:HAS_CONSENSUS]->(c:Consensus) RETURN d.query as point, c.summary as solution, c.rationale as rationale LIMIT 50")
            
            # 2. Fallback to Local Cache (L5 Resilience)
            if not all_points:
                try:
                    with open(self.cache_path, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                        all_points = [
                            {"point": c["decision_point"], "solution": c["consensus_summary"], "rationale": c["rationale"]}
                            for c in cache
                        ]
                except:
                    all_points = []

            if all_points:
                from app.services.llm_gateway import llm_gateway
                points_str = "\n".join([f"[{i}] {p['point']}" for i, p in enumerate(all_points)])
                
                decision_prompt = f"""
                Current User Requirement: "{query}"
                Past Architectural Decisions (0-indexed):
                {points_str}
                
                Identify if any past decisions are SEMANTICALLY RELEVANT to the current requirement.
                If yes, return the index number of the MOST RELEVANT decision. 
                If multiple apply, pick the best one.
                If none apply, return -1.
                Only return the index number. No other text.
                """
                
                resp = await llm_gateway.call_tier(tier=1, prompt=decision_prompt, system_prompt="You are a Semantic Matcher.")
                try:
                    import re
                    match = re.search(r'-?\d+', resp.content)
                    idx = int(match.group()) if match else -1
                    if 0 <= idx < len(all_points):
                        results.append(all_points[idx])
                        logger.info(f"✨ [Subconscious] Semantic hit (Cache)! Linked to: {all_points[idx]['point']}")
                except:
                    pass
            
        return results[:5]
