# @covers REQ-007
from loguru import logger
from pydantic import BaseModel, Field


class AlignmentDecision(BaseModel):
    is_consistent: bool
    conflicts: list[str] = []
    # GOV-001: specific entities (people/orgs/concepts) at the centre of each conflict
    conflicting_entities: list[str] = []
    reinforcements: list[str] = []
    summary: str

    @property
    def severity(self) -> str:
        """Return 'clean' | 'low' | 'medium' | 'high' based on conflict count."""
        if self.is_consistent:
            return "clean"
        n = len(self.conflicts)
        if n >= 3:
            return "high"
        if n >= 1:
            return "medium"
        return "low"

class TruthAlignmentService:
    """
    负责校验图谱事实与向量分块内容的一致性。
    1. 实体识别对齐
    2. 关系矛盾校验
    3. 证据多重确认 (M2.3.1 Truth Alignment)
    """

    async def align(self, graph_facts: list[str], vector_contents: list[str]) -> AlignmentDecision:
        """
        对比图谱事实与向量内容。
        深度实现：使用 LLM 作为裁判，专门检测事实冲突。
        """
        if not graph_facts or not vector_contents:
            return AlignmentDecision(
                is_consistent=True,
                summary="无交叉数据，跳过对齐。"
            )

        from app.core.algorithms.classification import classifier_service

        # Define internal model for extraction
        class ConsistencyCheck(BaseModel):
            has_contradiction: bool = Field(..., description="Whether there is a direct logic contradiction between graph and vector content.")
            conflicts: list[str] = Field(default_factory=list, description="Specific descriptions of found contradictions.")
            conflicting_entities: list[str] = Field(
                default_factory=list,
                description="Entity names (people, organizations, dates, concept IDs) that appear in contradicting statements.",
            )
            reinforcements: list[str] = Field(default_factory=list, description="Facts that are explicitly confirmed by both sources.")
            analysis: str = Field(..., description="Brief reasoning of the consistency state.")

        # Construct prompt
        graph_str = "\n".join([f"- {f}" for f in graph_facts])
        vector_str = "\n\n".join([f"[Chunk {i}]: {c}" for i, c in enumerate(vector_contents)])

        prompt = (
            "Compare the following Knowledge Graph Facts with retrieved Text Chunks. "
            "Identify if there are any LOGICAL CONTRADICTIONS (e.g., status mismatch, date conflict, entity role swap).\n\n"
            "### Knowledge Graph Facts:\n"
            f"{graph_str}\n\n"
            "### Retrieved Text Chunks:\n"
            f"{vector_str}"
        )

        try:
            logger.info(f"⚖️ [TruthAlignment] Cross-verifying {len(graph_facts)} facts vs {len(vector_contents)} chunks via LLM")
            result = await classifier_service.extract_model(
                text=prompt,
                target_model=ConsistencyCheck,
                instruction="You are a data governance auditor. Your goal is to detect factual inconsistencies in RAG results. Be objective."
            )

            summary = result.analysis
            if result.has_contradiction:
                summary = f"⚠️ CONFLICT: {result.analysis}"

            return AlignmentDecision(
                is_consistent=not result.has_contradiction,
                conflicts=result.conflicts,
                conflicting_entities=result.conflicting_entities,
                reinforcements=result.reinforcements,
                summary=summary,
            )

        except Exception as e:
            logger.error(f"Alignment LLM call failed: {e}")
            return AlignmentDecision(
                is_consistent=True, # Fail open to avoid blocking
                summary=f"对齐校验异常: {e}"
            )

truth_alignment_service = TruthAlignmentService()
