"""
Graph Community Detection and Summarization matching Leiden algorithmic principles.
Uses networkx to identify communities of densely connected entities in Neo4j,
and utilizes the LLM to generate higher-level community summaries.
"""

from typing import Any

import networkx as nx
from loguru import logger

from app.core.graph_store import get_graph_store
from app.core.llm import LLMService


class GraphCommunityService:
    def __init__(self):
        self.store = get_graph_store()
        self.llm = LLMService()

    async def detect_and_summarize(self, kb_id: str) -> dict[str, Any]:
        """
        Pull subgraph for the given kb_id, detect communities,
        assign community IDs, and generate a summary for each community.
        """
        if not self.store.driver:
            return {"status": "error", "message": "Neo4j is not available."}

        logger.info(f"Starting community detection for KB: {kb_id}")

        # 1. Fetch graph for the specific KB
        query = """
        MATCH (n {kb_id: $kb_id})-[r]->(m {kb_id: $kb_id})
         RETURN n.id AS source,
             n.name AS source_name,
             type(r) AS rel_type,
             r.description AS rel_desc,
             m.id AS target,
             m.name AS target_name
        """
        results = self.store.query(query, {"kb_id": kb_id})

        if not results:
            return {"status": "skipped", "message": "No connected graph data found for this KB."}

        # 2. Build networkx graph
        graph = nx.Graph()
        node_details = {}
        for row in results:
            src = row["source"]
            tgt = row["target"]
            graph.add_edge(src, tgt, type=row["rel_type"], desc=row["rel_desc"])
            node_details[src] = row["source_name"] or src
            node_details[tgt] = row["target_name"] or tgt

        if len(graph.nodes) == 0:
            return {"status": "skipped", "message": "Graph is empty."}

        # 3. Community Detection (Using Louvain as a fallback for Leiden if leidenalg isn't installed)
        try:
            # networkx >= 2.6 has louvain
            communities = nx.community.louvain_communities(graph, seed=42)
        except Exception as e:
            logger.warning(f"Louvain failed, falling back to greedy modularity: {e}")
            communities = nx.community.greedy_modularity_communities(graph)

        # 4. Summarize each community using LLM
        community_summaries = []

        for idx, comm in enumerate(communities):
            community_id = f"{kb_id}_comm_{idx}"

            # Extract subgraph for this community to provide context to LLM
            subgraph_nodes = list(comm)
            subgraph = graph.subgraph(subgraph_nodes)

            # Create a textual representation of the community
            entities_text = ", ".join([node_details.get(n, str(n)) for n in subgraph_nodes])
            edges_text = "\n".join(
                [
                    f"{u} -> {data.get('type')} -> {v} ({data.get('desc', '')})"
                    for u, v, data in subgraph.edges(data=True)
                ]
            )

            prompt = f"""You are a GraphRAG Community Summarizer.
Analyze the following tightly connected community of entities and relationships.
Provide a concise, comprehensive summary explaining what this community represents as a whole and the key themes.

Entities:
{entities_text}

Relationships:
{edges_text}

Summary:
"""
            # Call LLM
            summary = ""
            try:
                response = await self.llm.chat_complete(
                    [
                        {"role": "system", "content": "You are a helpful knowledge analyst."},
                        {"role": "user", "content": prompt},
                    ]
                )
                summary = response.strip()
            except Exception as e:
                logger.error(f"Failed to summarize community {community_id}: {e}")
                summary = f"Community of {len(subgraph_nodes)} entities."

            # Update Neo4j with Community ID and Summary
            update_query = """
            MATCH (n {kb_id: $kb_id})
            WHERE n.id IN $node_ids
            SET n.community = $community_id

            MERGE (c:Community {id: $community_id, kb_id: $kb_id})
            SET c.summary = $summary, c.size = $size
            """
            self.store.query(
                update_query,
                {
                    "kb_id": kb_id,
                    "node_ids": subgraph_nodes,
                    "community_id": community_id,
                    "summary": summary,
                    "size": len(subgraph_nodes),
                },
            )

            community_summaries.append({"community_id": community_id, "size": len(subgraph_nodes), "summary": summary})

        logger.info(f"Detected and summarized {len(communities)} communities for KB {kb_id}.")
        return {"status": "success", "communities": len(communities), "data": community_summaries}
