"""
Multi-Swarm Pipeline — 多 Swarm 协作的流水线架构。

核心设计:
    Swarm 之间通过 Artifact 通信，而非 Message。
    每个 Stage 定义: 需要什么输入 → 产出什么 Artifact → 传递什么给下游。

信息分类:
    ✅ 有用 (传递给下游):
        - 结构化提取结果 (JSON/dict)
        - 关键决策和判断 (分类结果、风险评估)
        - 可操作的数据 (表格、数据点、代码)
        - 置信度和元数据

    ❌ 无用 (不传递):
        - Swarm 内部对话历史 (Supervisor ↔ Agent 的往来)
        - Retry / 错误恢复过程
        - Agent 的思考链 (除非后续需要审计)
        - 格式化的 Markdown 输出 (给人看的，不给下游 Swarm)

架构图:
    File → [Stage A] → Artifact A → [Stage B] → Artifact B → [Stage C] → Final
                 ↓                        ↓                        ↓
           内部对话 (丢弃)           内部对话 (丢弃)           内部对话 (丢弃)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable, Optional

from pydantic import BaseModel, Field
from loguru import logger
import time


# ============================================================
#  Artifact — Swarm 之间的通信协议
# ============================================================

class ArtifactType(str, Enum):
    """产物类型。"""
    EXTRACTED_DATA = "extracted_data"       # 结构化提取 (JSON)
    ANALYSIS_RESULT = "analysis_result"     # 分析结论
    CLASSIFICATION = "classification"       # 分类标签
    SUMMARY = "summary"                     # 摘要
    CODE = "code"                           # 生成的代码
    TABLE = "table"                         # 表格数据
    DECISION = "decision"                   # 决策 (是/否/待定)
    REPORT = "report"                       # 最终报告
    ERROR = "error"                         # 错误信息


class Artifact(BaseModel):
    """
    Swarm 产出的结构化产物 — 唯一的跨 Swarm 通信载体。

    设计原则:
        1. 必须是结构化的 (能被下游程序解析)
        2. 必须是自描述的 (不看上游对话也能理解)
        3. 必须有元数据 (谁产出的、什么时候、多可信)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # --- 内容 ---
    artifact_type: ArtifactType
    data: dict[str, Any]           # 核心数据 (结构化)
    text_summary: str = ""         # 一句话摘要 (给下游 Swarm 的 prompt 用)

    # --- 元数据 ---
    source_stage: str = ""         # 产出这个 Artifact 的 Stage 名
    source_file: str = ""          # 原始文件标识
    confidence: float = 1.0        # 置信度 0.0-1.0
    warnings: list[str] = []       # 注意事项 (如 "数据不完整")

    # --- 追踪 ---
    created_at: datetime = Field(default_factory=datetime.utcnow)
    token_cost: int = 0            # 产出这个 Artifact 花了多少 token


class StageInput(BaseModel):
    """
    Stage 的标准化输入。

    每个 Stage 收到的不是"上一个 Swarm 的对话历史"，
    而是"精心筛选过的 Artifact 集合 + 原始数据"。
    """
    # --- 原始数据 ---
    raw_content: str = ""          # 原始文件内容 (仅第一个 Stage 需要)
    file_metadata: dict[str, Any] = {}  # 文件名、大小、类型等

    # --- 来自上游的 Artifact ---
    upstream_artifacts: list[Artifact] = []

    # --- 全局共享上下文 ---
    pipeline_context: dict[str, Any] = {}  # 整个 Pipeline 共享的配置/参数
    job_id: str = ""

    def get_artifact(self, stage_name: str) -> Artifact | None:
        """获取特定 Stage 的产物。"""
        for a in self.upstream_artifacts:
            if a.source_stage == stage_name:
                return a
        return None

    def get_artifacts_by_type(self, artifact_type: ArtifactType) -> list[Artifact]:
        """按类型获取产物。"""
        return [a for a in self.upstream_artifacts if a.artifact_type == artifact_type]

    def build_context_summary(self, max_chars: int = 2000) -> str:
        """
        为下游 Swarm 构建上下文摘要。

        这是最关键的方法 — 决定"传什么给 LLM"。
        """
        parts = []
        total_chars = 0

        for artifact in self.upstream_artifacts:
            summary = (
                f"[来自 {artifact.source_stage}] "
                f"({artifact.artifact_type.value}, "
                f"置信度={artifact.confidence:.0%}): "
                f"{artifact.text_summary}"
            )

            if total_chars + len(summary) > max_chars:
                parts.append("... (更多上游结果已省略，以节省上下文窗口)")
                break

            parts.append(summary)
            total_chars += len(summary)

        return "\n".join(parts)


# ============================================================
#  Pipeline Stage — 流水线的一个阶段
# ============================================================

class StageDefinition(BaseModel):
    """流水线中一个 Stage 的定义。"""
    name: str                      # 如 "extract", "analyze", "report"
    description: str               # 人类可读描述
    agent_name: str | None = None  # 指定 Agent (None = Supervisor 路由)

    # --- 输入/输出契约 ---
    required_inputs: list[str] = []     # 需要哪些上游 Stage 的 Artifact
    output_artifact_type: ArtifactType = ArtifactType.EXTRACTED_DATA

    # --- 提取规则: 告诉这个 Stage "从 Swarm 输出中提取什么" ---
    extraction_schema: dict[str, Any] = {}  # JSON Schema 描述期望的输出结构

    # --- 配置 ---
    timeout: int = 120
    max_retries: int = 2
    prompt_template: str = ""      # 特定于此 Stage 的 Prompt 模板名


# ============================================================
#  Pipeline Definition — 完整流水线
# ============================================================

class PipelineDefinition(BaseModel):
    """
    定义一条完整的处理流水线。

    示例 (文档分析流水线):
        Stage 1: extract    → 从原始文件提取结构化数据
        Stage 2: classify   → 对提取的数据进行分类
        Stage 3: analyze    → 深度分析 (依赖 extract + classify)
        Stage 4: report     → 生成最终报告 (依赖 analyze)
    """
    name: str
    description: str = ""
    stages: list[StageDefinition] = []

    def get_stage(self, name: str) -> StageDefinition | None:
        for s in self.stages:
            if s.name == name:
                return s
        return None

    def get_execution_order(self) -> list[list[str]]:
        """
        计算执行顺序 (拓扑排序)。
        返回分层列表: 同一层的 Stage 可以并行。

        示例:
            [["extract"], ["classify", "summarize"], ["analyze"], ["report"]]
              ↑ 第一层       ↑ 第二层 (可并行)       ↑ 第三层      ↑ 第四层
        """
        # Build dependency graph
        stage_names = {s.name for s in self.stages}
        deps: dict[str, set[str]] = {}
        for s in self.stages:
            deps[s.name] = {r for r in s.required_inputs if r in stage_names}

        layers: list[list[str]] = []
        resolved: set[str] = set()

        while len(resolved) < len(stage_names):
            # Find stages whose deps are all resolved
            layer = [
                name for name, d in deps.items()
                if name not in resolved and d.issubset(resolved)
            ]
            if not layer:
                raise ValueError("Circular dependency in pipeline stages")
            layers.append(layer)
            resolved.update(layer)

        return layers


# ============================================================
#  Pipeline Executor — 流水线执行器
# ============================================================

class PipelineExecutor:
    """
    执行一条流水线，管理 Stage 之间的 Artifact 传递。

    关键职责:
        1. 按拓扑排序执行 Stage
        2. 为每个 Stage 构建 StageInput (只传需要的 Artifact)
        3. 从 Swarm 输出中提取 Artifact
        4. 管理全局 Artifact 存储
    """

    def __init__(
        self,
        pipeline: PipelineDefinition,
        swarm_invoke_fn: Callable[[str, dict[str, Any]], Awaitable[dict]] | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._swarm_invoke_fn = swarm_invoke_fn
        self._artifacts: dict[str, Artifact] = {}  # stage_name → Artifact
        self._stage_traces: dict[str, dict] = {}    # 调试用: stage → 完整 swarm 状态
        
        # Lifecycle Hooks (for logging/monitoring)
        self.on_job_start: Optional[Callable[[dict[str, Any]], Awaitable[None]]] = None
        self.on_job_end: Optional[Callable[[dict[str, Artifact]], Awaitable[None]]] = None
        self.on_stage_start: Optional[Callable[[str, StageInput], Awaitable[None]]] = None
        self.on_stage_end: Optional[Callable[[str, Artifact, int], Awaitable[None]]] = None # stage_name, artifact, duration_ms

        logger.info(f"🔗 PipelineExecutor created: {pipeline.name} ({len(pipeline.stages)} stages)")

    async def execute(
        self,
        raw_content: str,
        file_metadata: dict[str, Any] | None = None,
        pipeline_context: dict[str, Any] | None = None,
    ) -> dict[str, Artifact]:
        """
        执行整条流水线。

        Args:
            raw_content: 原始文件内容
            file_metadata: 文件元数据
            pipeline_context: 全局共享上下文

        Returns:
            stage_name → Artifact 的完整映射
        """
        file_metadata = file_metadata or {}
        pipeline_context = pipeline_context or {}

        execution_order = self._pipeline.get_execution_order()
        logger.info(
            f"🚀 Pipeline [{self._pipeline.name}] starting | "
            f"Stages: {' → '.join(['/'.join(layer) for layer in execution_order])}"
        )

        # 1. Job Start Hook
        on_job_start = self.on_job_start
        if on_job_start:
            await on_job_start({
                "pipeline_name": self._pipeline.name,
                "file_metadata": file_metadata,
                "pipeline_context": pipeline_context,
                "total_stages": len(self._pipeline.stages)
            })

        import asyncio

        for layer_idx, layer in enumerate(execution_order):
            logger.info(f"📍 Layer {layer_idx + 1}/{len(execution_order)}: {layer}")

            # 同一层可以并行
            tasks = []
            for stage_name in layer:
                stage_def = self._pipeline.get_stage(stage_name)
                if not stage_def:
                    continue

                stage_input = self._build_stage_input(
                    stage_def=stage_def,
                    raw_content=raw_content if layer_idx == 0 else "",  # 只有第一层拿原始内容
                    file_metadata=file_metadata,
                    pipeline_context=pipeline_context,
                )

                # 2. Stage Start Hook
                on_stage_start = self.on_stage_start
                if on_stage_start:
                    await on_stage_start(stage_name, stage_input)

                async def _timed_execution(sd, si):
                    start_t = time.perf_counter()
                    on_stage_end = self.on_stage_end
                    try:
                        res = await self._execute_stage(sd, si)
                        duration = int((time.perf_counter() - start_t) * 1000)
                        
                        # 3. Stage End Hook
                        if on_stage_end:
                            await on_stage_end(sd.name, res, duration)
                        return res
                    except Exception as e:
                        duration = int((time.perf_counter() - start_t) * 1000)
                        err_art = Artifact(
                            artifact_type=ArtifactType.ERROR,
                            data={"error": str(e)},
                            text_summary=f"Stage Exception: {e}",
                            source_stage=sd.name,
                            confidence=0.0
                        )
                        if on_stage_end:
                            await on_stage_end(sd.name, err_art, duration)
                        raise e

                tasks.append(_timed_execution(stage_def, stage_input))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for stage_name, result in zip(layer, results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Stage [{stage_name}] failed: {result}")
                    self._artifacts[stage_name] = Artifact(
                        artifact_type=ArtifactType.ERROR,
                        data={"error": str(result)},
                        text_summary=f"Stage failed: {result}",
                        source_stage=stage_name,
                        confidence=0.0,
                    )
                else:
                    self._artifacts[stage_name] = result
                    
                # --- Short-circuit logic for Audit/Security (M2.1D) ---
                if not isinstance(result, Exception):
                    status = result.data.get("status")
                    if status in ["pending", "rejected"]:
                        logger.warning(f"🛑 Pipeline HALTED at stage [{stage_name}] due to status: {status}")
                        on_job_end = self.on_job_end
                        if on_job_end:
                            await on_job_end(self._artifacts)
                        return self._artifacts

        on_job_end = self.on_job_end
        if on_job_end:
            await on_job_end(self._artifacts)

        logger.success(
            f"✅ Pipeline [{self._pipeline.name}] completed | "
            f"Artifacts: {len(self._artifacts)}"
        )
        return self._artifacts

    def _build_stage_input(
        self,
        stage_def: StageDefinition,
        raw_content: str,
        file_metadata: dict[str, Any],
        pipeline_context: dict[str, Any],
    ) -> StageInput:
        """
        为一个 Stage 构建输入 — 这是"信息筛选"的核心。

        规则:
            1. 只传递 required_inputs 声明的 Artifact (不是全部)
            2. 如果 required_inputs 为空，传递所有已有 Artifact
            3. 原始内容只给第一个 Stage
        """
        if stage_def.required_inputs:
            # 精确匹配: 只给声明需要的
            upstream = [
                self._artifacts[name]
                for name in stage_def.required_inputs
                if name in self._artifacts
            ]
        else:
            # 没声明依赖: 给所有已有的 (第一个 Stage 通常走这里)
            upstream = list(self._artifacts.values())

        return StageInput(
            raw_content=raw_content,
            file_metadata=file_metadata,
            upstream_artifacts=upstream,
            pipeline_context=pipeline_context,
        )

    async def _execute_stage(
        self,
        stage_def: StageDefinition,
        stage_input: StageInput,
    ) -> Artifact:
        """
        执行单个 Stage。

        流程:
            1. 构建 Prompt (包含上游 Artifact 摘要)
            2. 调用 Swarm
            3. 从 Swarm 输出中提取结构化 Artifact
        """
        # 构建给 Swarm 的 Prompt
        context_summary = stage_input.build_context_summary(max_chars=3000)

        prompt = f"""
## Task: {stage_def.name}
{stage_def.description}

## Input File
{stage_input.raw_content[:2000] if stage_input.raw_content else "(See upstream artifacts below)"}
{"... (truncated)" if len(stage_input.raw_content) > 2000 else ""}

## File Metadata
{stage_input.file_metadata}

{"## Upstream Results" if context_summary else ""}
{context_summary}

## Expected Output
Return a JSON object with your analysis results.
{f"Schema: {stage_def.extraction_schema}" if stage_def.extraction_schema else ""}
"""

        if self._swarm_invoke_fn:
            swarm_result = await self._swarm_invoke_fn(prompt, {
                "stage": stage_def.name,
                "pipeline_context": stage_input.pipeline_context,
            })

            # 从 Swarm 结果中提取 Artifact
            return self._extract_artifact(stage_def, swarm_result)
        else:
            # Mock 模式
            import asyncio
            await asyncio.sleep(0.3)
            return Artifact(
                artifact_type=stage_def.output_artifact_type,
                data={"mock": True, "stage": stage_def.name},
                text_summary=f"[Mock] {stage_def.name} 完成",
                source_stage=stage_def.name,
                source_file=stage_input.file_metadata.get("filename", ""),
                confidence=0.9,
            )

    def _extract_artifact(
        self,
        stage_def: StageDefinition,
        swarm_result: dict,
    ) -> Artifact:
        """
        从 Swarm 输出中提取结构化 Artifact。

        这是"丢弃无用信息"的关键步骤:
            - Swarm 返回的 messages 列表 → 丢弃
            - Swarm 的 agent_outputs → 提取最终结果
            - Swarm 的内部状态 → 丢弃
        """
        # 取 Swarm 的最终输出 (最后一条 AI 消息)
        messages = swarm_result.get("messages", [])
        final_content = ""
        if messages:
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    final_content = msg.content
                    break

        # 尝试从输出中解析 JSON
        import json
        data = {}
        try:
            # 清理 markdown
            content = final_content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            data = json.loads(content)
        except Exception:
            data = {"raw_text": final_content}

        return Artifact(
            artifact_type=stage_def.output_artifact_type,
            data=data,
            text_summary=final_content[:200],  # 前 200 字符作为摘要
            source_stage=stage_def.name,
            confidence=0.8,  # 默认值，可由 Stage 逻辑调整
        )

    def get_artifact(self, stage_name: str) -> Artifact | None:
        return self._artifacts.get(stage_name)

    def get_all_artifacts(self) -> dict[str, Artifact]:
        return self._artifacts.copy()

    def get_final_artifact(self) -> Artifact | None:
        """获取最后一个 Stage 的产物。"""
        if not self._pipeline.stages:
            return None
        last_stage = self._pipeline.stages[-1].name
        return self._artifacts.get(last_stage)
