"""
HiveMind Research Agent (Specialized Worker)

Purpose: Retrieves and summarizes information from the HiveMind Knowledge Base.
Integration: Calls RAGGateway for high-fidelity retrieval.
"""

from typing import Any

from loguru import logger

from app.services.agents.protocol import AgentTask
from app.services.agents.worker import WorkerAgent
from app.services.llm_gateway import llm_gateway
from app.services.rag_gateway import RAGGateway


class ResearchAgent(WorkerAgent):
    def __init__(self, kb_ids: list[str] | None = None):
        super().__init__(
            name="ResearchAgent",
            description="Expert in retrieving, synthesizing and verifying knowledge from the corporate KB."
        )
        self.kb_ids = kb_ids or []
        self.gw = RAGGateway()

    async def _run_logic(self, task: AgentTask) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Worker's specialized logic: RAG-based Research with Collective Intelligence (Blackboard)."""
        logger.info(f"ResearchAgent researching for task: {task.instruction}")

        # 🧠 Swarm Advantage: Check what we ALREADY know from other agents (Research-Code collaboration)
        if task.blackboard:
            # Optionally adjust retrieval based on what others found
            logger.debug(f"ResearchAgent utilizing blackboard with {len(task.blackboard)} previous results.")

        # 1. RAG Retrieval
        res = await self.gw.retrieve(
            query=task.instruction,
            kb_ids=self.kb_ids,
            user_id="supervisor_system",
            top_k=8
        )

        if not res.fragments:
            return "No relevant information found in knowledge base.", {}, {"status": "NO_RECORDS"}

        context_str = "\n".join([f"[{i}] {f.content}" for i, f in enumerate(res.fragments)])

        # 2. LLM Synthesis
        # We can now inject findings from OTHER agents to refine our summary
        blackboard_summary = ""
        if task.blackboard:
            blackboard_summary = "\nExisting HiveMind Knowledge:\n" + "\n".join([f"- {k}: {str(v)[:100]}..." for k, v in task.blackboard.items()])

        system_prompt = f"""
        You are the HiveMind Research Agent.
        Your goal is to synthesize the provided research fragments into a clear, concise summary.
        Objective: {task.instruction}
        {blackboard_summary}
        
        Fragments:
        {context_str}
        """

        synth_response = await llm_gateway.call_tier(
            tier=2,
            prompt=f"Synthesize research for: {task.instruction}",
            system_prompt=system_prompt
        )

        # 💡 Return Intelligence Signal
        # Example: if we find critical security info, we signal "SECURITY_HINT"
        doc_ids = list(set([f.metadata.get("document_id") for f in res.fragments]))
        signal = {"found_docs": len(doc_ids)}
        if "security" in synth_response.content.lower():
            signal["requires_audit"] = True

        # 🔗 M9.2.1: 事实声明验证 — 检查合成结果中的关键声明是否有检索证据支持
        try:
            ungrounded = self._check_factual_grounding(synth_response.content, context_str)
            if ungrounded:
                signal["ungrounded_claims"] = ungrounded
                signal["grounding_warning"] = True
                logger.info(
                    f"🔍 [ResearchAgent] {len(ungrounded)} potentially ungrounded claim(s) detected"
                )
        except Exception as e:
            logger.debug(f"Factual grounding check skipped: {e}")

        return synth_response.content, {"doc_ids": doc_ids}, signal

    @staticmethod
    def _check_factual_grounding(synthesis: str, evidence: str) -> list[str]:
        """
        M9.2.1: 轻量级事实声明验证（Computational，不调用 LLM）。

        检查合成文本中的数字、百分比、专有名词等"硬声明"是否出现在检索证据中。
        返回未被证据支持的声明列表。
        """
        import re

        ungrounded: list[str] = []
        evidence_lower = evidence.lower()

        # 提取合成文本中的"硬声明"模式
        patterns = [
            # 数字 + 单位（如 "99.9%", "10x", "3.5 billion"）
            (r"\b\d+\.?\d*\s*[%xX×]\b", "numeric claim"),
            # 年份引用（如 "in 2025", "since 2023"）
            (r"\b(?:in|since|by|from)\s+20[2-3]\d\b", "temporal claim"),
            # 引用特定工具/框架名（首字母大写的专有名词序列）
            (r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b", "proper noun"),
        ]

        for pattern, claim_type in patterns:
            matches = re.findall(pattern, synthesis)
            for match in matches:
                # 检查这个声明是否在检索证据中有支持
                if match.lower() not in evidence_lower:
                    # 对专有名词做更宽松的匹配（单词级）
                    if claim_type == "proper noun":
                        words = match.lower().split()
                        if any(w in evidence_lower for w in words if len(w) > 3):
                            continue  # 至少有一个关键词匹配，放行
                    ungrounded.append(f"[{claim_type}] {match}")

        # 去重并限制数量
        seen = set()
        result = []
        for claim in ungrounded:
            if claim not in seen:
                seen.add(claim)
                result.append(claim)
            if len(result) >= 5:
                break

        return result
