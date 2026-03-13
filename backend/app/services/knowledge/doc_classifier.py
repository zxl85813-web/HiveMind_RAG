"""
Document Classifier v1 — TASK-KV-002

将文档资产分类为：adr / req / design / runbook / meeting / api_spec / unknown

策略（两阶段，优先规则，降级 LLM）：
  1. 规则层：基于文件名、路径关键词快速匹配（无 LLM 成本）
  2. LLM 层：规则无法确定时，用 classifier_service 从内容推断

用法：
    classifier = DocClassifier()
    result = await classifier.classify(path="docs/ADR-001.md")
    result = await classifier.classify(path="queries/report.sql", content="...")
"""

import re
from enum import StrEnum

from loguru import logger

from app.schemas.artifact import DocType


# --- 规则映射表（路径/文件名关键词 -> DocType）---

_PATH_RULES: list[tuple[re.Pattern, DocType]] = [
    (re.compile(r"\badr[-_]?\d*\b", re.IGNORECASE), DocType.ADR),
    (re.compile(r"architecture[_-]decision", re.IGNORECASE), DocType.ADR),
    (re.compile(r"\breq[-_]?\d+\b", re.IGNORECASE), DocType.REQ),
    (re.compile(r"requirement", re.IGNORECASE), DocType.REQ),
    (re.compile(r"\bdes[-_]?\d+\b", re.IGNORECASE), DocType.DESIGN),
    (re.compile(r"\bdesign\b", re.IGNORECASE), DocType.DESIGN),
    (re.compile(r"architecture", re.IGNORECASE), DocType.DESIGN),
    (re.compile(r"runbook", re.IGNORECASE), DocType.RUNBOOK),
    (re.compile(r"playbook", re.IGNORECASE), DocType.RUNBOOK),
    (re.compile(r"operations?[-_]guide", re.IGNORECASE), DocType.RUNBOOK),
    (re.compile(r"meeting[-_]?(note|minute|record)", re.IGNORECASE), DocType.MEETING),
    (re.compile(r"(weekly|daily|sprint|standup)[-_]?(report|note|recap)", re.IGNORECASE), DocType.MEETING),
    (re.compile(r"openapi|swagger|api[-_]?spec", re.IGNORECASE), DocType.API_SPEC),
    (re.compile(r"\.(yaml|yml|json)$", re.IGNORECASE), DocType.API_SPEC),  # openspec files
]


class ClassificationResult(StrEnum):
    RULE = "rule"    # 规则命中
    LLM = "llm"      # LLM 推断
    FALLBACK = "fallback"  # 兜底


class DocClassificationOutput:
    """分类结果，附带置信度与来源。"""

    def __init__(self, doc_type: DocType, confidence: float, source: ClassificationResult, reason: str = ""):
        self.doc_type = doc_type
        self.confidence = confidence
        self.source = source
        self.reason = reason

    def __repr__(self) -> str:
        return f"DocClassificationOutput(type={self.doc_type}, confidence={self.confidence:.2f}, source={self.source})"


class DocClassifier:
    """文档分类器 v1：规则优先，LLM 降级。"""

    async def classify(
        self,
        path: str,
        content: str | None = None,
        use_llm_fallback: bool = True,
    ) -> DocClassificationOutput:
        """
        分类单个文档。

        Args:
            path: 文件路径（相对或绝对，用于规则匹配）
            content: 文档内容前 2000 字（规则无法判断时传给 LLM）
            use_llm_fallback: 是否允许调用 LLM（False 时仅规则，unknown 兜底）

        Returns:
            DocClassificationOutput
        """
        # 阶段 1：规则层
        rule_result = self._classify_by_rules(path)
        if rule_result is not None:
            logger.debug(f"[DocClassifier] Rule hit: {path} -> {rule_result}")
            return DocClassificationOutput(
                doc_type=rule_result,
                confidence=0.95,
                source=ClassificationResult.RULE,
                reason=f"Path pattern matched: {path}",
            )

        # 阶段 2：LLM 层
        if use_llm_fallback and content:
            try:
                llm_result = await self._classify_by_llm(path, content)
                return llm_result
            except Exception as e:
                logger.warning(f"[DocClassifier] LLM fallback failed for {path}: {e}")

        return DocClassificationOutput(
            doc_type=DocType.UNKNOWN,
            confidence=0.0,
            source=ClassificationResult.FALLBACK,
            reason="No rule matched and LLM unavailable or no content provided.",
        )

    def _classify_by_rules(self, path: str) -> DocType | None:
        """按文件名/路径关键词规则匹配。返回 None 表示未命中。"""
        # 取文件名部分（不带目录）+ 完整路径都参与匹配
        filename = path.split("/")[-1].split("\\")[-1]
        target = f"{path} {filename}"

        for pattern, doc_type in _PATH_RULES:
            if pattern.search(target):
                return doc_type
        return None

    async def _classify_by_llm(self, path: str, content: str) -> DocClassificationOutput:
        """调用 LLM 从内容推断文档类型。"""
        from pydantic import BaseModel, Field

        from app.core.algorithms.classification import classifier_service

        class DocTypeExtraction(BaseModel):
            doc_type: str = Field(
                ...,
                description=(
                    "Document category. Must be one of: "
                    "adr, req, design, runbook, meeting, api_spec, unknown"
                ),
            )
            confidence: float = Field(default=0.8, description="Confidence score 0.0-1.0")
            reason: str = Field(default="", description="Brief reason for this classification")

        snippet = content[:2000]
        prompt = (
            f"File path: {path}\n\n"
            f"Content snippet:\n{snippet}\n\n"
            "Classify this document into one of the categories: "
            "adr (architecture decision), req (requirement), design (design doc), "
            "runbook (operations guide), meeting (meeting notes), api_spec (API specification), unknown."
        )

        result = await classifier_service.extract_model(
            text=prompt,
            target_model=DocTypeExtraction,
            instruction="You are a technical document classifier. Output in JSON.",
        )

        # 安全映射（LLM 可能返回非法值）
        try:
            doc_type = DocType(result.doc_type.lower())
        except ValueError:
            doc_type = DocType.UNKNOWN

        return DocClassificationOutput(
            doc_type=doc_type,
            confidence=result.confidence,
            source=ClassificationResult.LLM,
            reason=result.reason,
        )

    async def classify_batch(
        self,
        paths: list[str],
        contents: dict[str, str] | None = None,
        use_llm_fallback: bool = True,
    ) -> dict[str, DocClassificationOutput]:
        """批量分类文档（路径 -> 分类结果）。"""
        import asyncio

        contents = contents or {}
        tasks = {
            path: self.classify(path, content=contents.get(path), use_llm_fallback=use_llm_fallback)
            for path in paths
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        output: dict[str, DocClassificationOutput] = {}
        for path, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                output[path] = DocClassificationOutput(DocType.UNKNOWN, 0.0, ClassificationResult.FALLBACK, str(result))
            elif isinstance(result, DocClassificationOutput):
                output[path] = result
        return output


# 全局单例
doc_classifier = DocClassifier()
