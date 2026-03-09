"""
Pipeline 示例 + 测试.

模拟场景: 合同文件分析流水线
    Stage 1: extract    - 从合同中提取关键条款 (金额、日期、甲乙方)
    Stage 2: classify   - 判断合同类型和风险等级 (可与 extract 并行? 不, 它依赖 extract)
    Stage 3: summarize  - 生成摘要 (只需要 extract 的结果)
    Stage 4: risk_check - 风险检查 (需要 extract + classify 两个上游)
    Stage 5: report     - 生成最终报告 (需要所有上游)

DAG 依赖图:
    extract --> classify ---> risk_check --> report
       |                         ^
       +--> summarize            |
              +------------------+

执行顺序 (拓扑排序):
    Layer 1: [extract]
    Layer 2: [classify, summarize]  - 这两个可以并行!
    Layer 3: [risk_check]
    Layer 4: [report]

信息传递规则:
    +--------------------------------------------------------------+
    | Stage        | 拿到什么              | 丢弃什么              |
    |--------------|-----------------------|----------------------|
    | extract      | 原始文件内容           | -                    |
    | classify     | extract 的结构化JSON   | extract 的对话历史    |
    | summarize    | extract 的结构化JSON   | extract 的对话历史    |
    | risk_check   | extract + classify    | 两者的对话历史        |
    |              | 的 Artifact           | + summarize (不需要)  |
    | report       | 所有 4 个 Artifact    | 所有对话历史          |
    +--------------------------------------------------------------+
"""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from loguru import logger  # noqa: E402

from app.batch.pipeline import (  # noqa: E402
    ArtifactType,
    PipelineDefinition,
    PipelineExecutor,
    StageDefinition,
)


def build_contract_pipeline() -> PipelineDefinition:
    """构建合同分析流水线."""
    return PipelineDefinition(
        name="contract_analysis",
        description="合同文件全面分析流水线",
        stages=[
            StageDefinition(
                name="extract",
                description="从合同文本中提取关键信息: 甲方、乙方、金额、日期、条款.",
                output_artifact_type=ArtifactType.EXTRACTED_DATA,
                required_inputs=[],  # 第一个阶段, 无上游依赖
                extraction_schema={
                    "party_a": "str - 甲方名称",
                    "party_b": "str - 乙方名称",
                    "amount": "float - 合同金额",
                    "currency": "str - 币种",
                    "start_date": "str - 起始日期",
                    "end_date": "str - 结束日期",
                    "key_clauses": "list[str] - 关键条款摘录",
                },
            ),
            StageDefinition(
                name="classify",
                description="根据提取的信息判断合同类型和风险等级.",
                output_artifact_type=ArtifactType.CLASSIFICATION,
                required_inputs=["extract"],  # - 精确声明依赖
                extraction_schema={
                    "contract_type": "str - 采购/服务/租赁/投资/其他",
                    "risk_level": "str - low/medium/high/critical",
                    "risk_factors": "list[str] - 风险因素",
                },
            ),
            StageDefinition(
                name="summarize",
                description="生成合同的中文摘要 (200字以内).",
                output_artifact_type=ArtifactType.SUMMARY,
                required_inputs=["extract"],  # - 只需要 extract, 不需要 classify
            ),
            StageDefinition(
                name="risk_check",
                description="综合分析合同风险: 法律合规性、财务风险、执行风险.",
                output_artifact_type=ArtifactType.ANALYSIS_RESULT,
                required_inputs=["extract", "classify"],  # - 需要两个上游
                extraction_schema={
                    "compliance_ok": "bool",
                    "financial_risk": "str",
                    "execution_risk": "str",
                    "recommendations": "list[str]",
                },
            ),
            StageDefinition(
                name="report",
                description="生成最终分析报告.",
                output_artifact_type=ArtifactType.REPORT,
                required_inputs=["extract", "classify", "summarize", "risk_check"],
            ),
        ],
    )


async def main():
    logger.info("🧪 Pipeline 流水线测试")

    # 1. 构建流水线定义
    pipeline = build_contract_pipeline()

    # 2. 查看执行顺序
    order = pipeline.get_execution_order()
    logger.info("📋 执行顺序:")
    for i, layer in enumerate(order):
        parallel_note = " (可并行)" if len(layer) > 1 else ""
        logger.info(f"   Layer {i + 1}: {layer}{parallel_note}")

    # 3. 创建执行器 (Mock 模式)
    executor = PipelineExecutor(pipeline=pipeline, swarm_invoke_fn=None)

    # 4. 模拟合同内容
    contract_text = """
    合同编号: HM-2026-0042
    甲方: 深圳智能科技有限公司
    乙方: 杭州数据服务有限公司

    一、合同金额: 人民币 1,500,000 元整
    二、合同期限: 2026年3月1日 至 2027年2月28日
    三、服务内容: 乙方为甲方提供 AI 数据标注服务...
    四、付款方式: 分三期支付...
    五、违约条款: 如任何一方违约...
    """

    # 5. 执行流水线
    artifacts = await executor.execute(
        raw_content=contract_text,
        file_metadata={"filename": "contract_HM-2026-0042.pdf", "size_kb": 256},
        pipeline_context={"language": "zh", "client": "test"},
    )

    # 6. 展示结果
    logger.success("\n" + "=" * 60)
    logger.success("📊 Pipeline 执行结果")
    logger.success("=" * 60)

    for stage_name, artifact in artifacts.items():
        logger.success(
            f"  [{stage_name:>12}] "
            f"type={artifact.artifact_type.value:<20} "
            f"confidence={artifact.confidence:.0%} "
            f"summary={artifact.text_summary[:50]}"
        )

    # 7. 展示信息传递路径
    logger.info("\n" + "=" * 60)
    logger.info("🔗 信息传递路径 (每个 Stage 收到了什么)")
    logger.info("=" * 60)

    for stage in pipeline.stages:
        inputs_str = ", ".join(stage.required_inputs) if stage.required_inputs else "原始文件内容"
        logger.info(f"  {stage.name}: 接收 <- [{inputs_str}]")

    # 8. 展示被丢弃的信息
    logger.info("\n" + "=" * 60)
    logger.info("🗑️ 被丢弃的信息 (不传递给下游)")
    logger.info("=" * 60)
    logger.info("  x 每个 Stage 内部 Supervisor <-> Agent 的对话历史")
    logger.info("  x Agent 的内部思考链 (Chain of Thought)")
    logger.info("  x Retry 过程中的失败尝试")
    logger.info("  x 格式化的 Markdown (给人看的)")
    logger.info("  x classify/summarize 不需要的 Artifact (如 risk_check 不要 summarize)")


if __name__ == "__main__":
    asyncio.run(main())
