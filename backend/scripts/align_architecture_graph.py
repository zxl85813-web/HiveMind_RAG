from app.sdk.core.graph_store import Neo4jStore
import asyncio
from loguru import logger

async def align_graph():
    """
    将 HCAR/AEC 架构组件同步到 Neo4j 架构图谱中。
    """
    store = Neo4jStore()
    
    # 核心对齐逻辑
    cypher = """
    // 1. 创建服务节点
    MERGE (s1:Service {name: 'QualityGovernanceService', id: 'SRV-QGS'})
    SET s1.description = '检索质量治理决策中心', 
        s1.layer = 'governance',
        s1.version = 'v1.0'
    
    MERGE (s2:Service {name: 'RefinementLab', id: 'SRV-RLAB'})
    SET s2.description = '策略对比与锦标赛实验室', 
        s2.layer = 'evaluation',
        s2.version = 'v1.0'
    
    // 2. 创建协议节点
    MERGE (p1:Protocol {name: 'KnowledgeQuality', id: 'PROT-KQ'})
    SET p1.description = 'RAG检索质量评估协议',
        p1.fields = ['max_score', 'avg_score', 'quality_tier']
    
    // 3. 关联 RAGGateway
    MERGE (gateway:Service {name: 'RAGGateway', id: 'SRV-RAG-GW'})
    MERGE (gateway)-[:USE_PROTOCOL]->(p1)
    MERGE (s1)-[:AUDITS]->(gateway)
    MERGE (s2)-[:TESTS]->(gateway)
    
    // 4. 关联数据模型
    MERGE (bc:Model {name: 'BadCase', id: 'MOD-BC'})
    MERGE (s2)-[:CONSUMES]->(bc)
    
    // 5. 标记 AEC (Active Evolution Cycle) 链路
    MERGE (aec:ArchitecturePattern {name: 'Active Evolution Cycle', id: 'PAT-AEC'})
    MERGE (s1)-[:PART_OF]->(aec)
    MERGE (s2)-[:PART_OF]->(aec)
    MERGE (gateway)-[:PART_OF]->(aec)
    
    RETURN count(*) as aligned_count
    """
    
    try:
        await store.execute_query(cypher)
        logger.info("✅ Graph Alignment Successful: AEC services and protocols mapped to Neo4j.")
    except Exception as e:
        logger.error(f"❌ Graph Alignment Failed: {e}")

if __name__ == "__main__":
    asyncio.run(align_graph())
