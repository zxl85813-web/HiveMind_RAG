"""
Agent + Skill interpretation engine for daily learning reports.

This module upgrades simple rule-based suggestions into a layered analysis pipeline:
1) Agent aggregates multi-source signals
2) Skills perform structured interpretation (themes, vendor landscape, priorities)
3) Agent optionally calls LLM to produce a concise strategic summary
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings


class SignalItem(BaseModel):
    source: str
    title: str
    url: str = ""
    origin: str = ""


class SkillRecommendation(BaseModel):
    priority: str
    title: str
    rationale: str
    action: str


class AgentInterpretation(BaseModel):
    summary: str
    learning_tracks: list[str]
    system_characteristics: list[str]
    key_risks: list[str]
    opportunities: list[str]
    seven_day_plan: list[str]
    classic_rag_optimizations: list[str]
    recommendations: list[SkillRecommendation]


@dataclass
class TrendClusteringSkill:
    """Cluster mixed signals into stable learning tracks."""

    name: str = "trend_clustering"

    def run(self, signals: list[SignalItem]) -> list[str]:
        buckets: dict[str, int] = defaultdict(int)
        for sig in signals:
            text = sig.title.lower()
            if any(k in text for k in ["rag", "retrieval", "search", "index"]):
                buckets["RAG 与检索质量"] += 1
            if any(k in text for k in ["agent", "swarm", "autogen", "workflow", "orchestration"]):
                buckets["Agent 编排与自治"] += 1
            if any(k in text for k in ["eval", "benchmark", "test", "regression", "quality"]):
                buckets["评测与质量工程"] += 1
            if any(k in text for k in ["release", "sdk", "api", "model"]):
                buckets["模型与平台能力更新"] += 1
            if any(k in text for k in ["security", "policy", "audit", "guardrail"]):
                buckets["安全与治理"] += 1

        if not buckets:
            return ["基础学习闭环（系统文档 + 项目任务 + 外部动态）"]

        ordered = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
        return [name for name, _ in ordered[:4]]


@dataclass
class VendorLandscapeSkill:
    """Extract multi-vendor AI landscape insights from signals."""

    name: str = "vendor_landscape"

    _vendors: tuple[str, ...] = (
        "openai",
        "anthropic",
        "deepmind",
        "google",
        "meta",
        "xai",
        "qwen",
        "alibaba",
        "mistral",
    )

    def run(self, signals: list[SignalItem]) -> str:
        seen = Counter()
        for sig in signals:
            text = f"{sig.title} {sig.origin}".lower()
            for vendor in self._vendors:
                if vendor in text:
                    seen[vendor] += 1

        if not seen:
            return "外部信号中暂未形成明显厂商格局，建议补充厂商关注源。"

        top = ", ".join([f"{k}:{v}" for k, v in seen.most_common(5)])
        return f"厂商信号覆盖度（Top）：{top}。建议做同题横向对比，避免单厂商路径依赖。"


@dataclass
class ImprovementPrioritizationSkill:
    """Prioritize improvements based on issue/project pressure and external trend signals."""

    name: str = "improvement_prioritization"

    def run(self, issue_titles: list[str], project_titles: list[str], tracks: list[str]) -> list[SkillRecommendation]:
        blob = " ".join(issue_titles + project_titles).lower()
        recs: list[SkillRecommendation] = []

        if any(k in blob for k in ["test", "regression", "qa", "coverage"]):
            recs.append(
                SkillRecommendation(
                    priority="P0",
                    title="建立学习结果到回归测试的映射",
                    rationale="项目任务已出现质量与回归压力，知识学习必须闭环到可验证测试。",
                    action="每日学习报告中新增‘学习点->测试用例’映射表，并在次日回看结果。",
                )
            )

        if any(k in blob for k in ["latency", "perf", "timeout", "slow", "memory"]):
            recs.append(
                SkillRecommendation(
                    priority="P1",
                    title="增加性能学习专题",
                    rationale="任务信号显示性能风险，应把外部方案转为本系统优化假设。",
                    action="每日报告至少给出一个性能优化假设和一个可观测指标。",
                )
            )

        if any(t == "Agent 编排与自治" for t in tracks):
            recs.append(
                SkillRecommendation(
                    priority="P1",
                    title="完善 Agent 决策可解释性",
                    rationale="学习轨道显示编排复杂度上升，需避免黑盒决策。",
                    action="给关键 Agent 路由决策增加‘原因字段’，并在日报中抽样审计。",
                )
            )

        if not recs:
            recs.append(
                SkillRecommendation(
                    priority="P2",
                    title="维持稳定学习节奏",
                    rationale="当前风险密度不高，适合持续迭代而非一次性重构。",
                    action="保持每日三段式输出：系统知识、项目变化、改进动作，并追踪执行率。",
                )
            )

        return recs[:4]


@dataclass
class ClassicRAGOptimizationSkill:
    """Provide stable, non-trendy RAG optimization playbook items."""

    name: str = "classic_rag_optimization"

    def run(self, tracks: list[str], issue_titles: list[str]) -> list[str]:
        blob = " ".join(issue_titles).lower()
        base = [
            "混合检索基线: 向量检索 + BM25 关键词召回，提升长尾命中率。",
            "查询改写: 对用户问句做同义扩展/意图归一，降低召回偏移。",
            "分块策略: parent-child chunking，召回短块、注入长块。",
            "重排策略: Cross-Encoder 或 LLM rerank，控制Top-K上下文质量。",
            "上下文压缩: 先粗召回再压缩，减少噪音与 token 浪费。",
            "离线评测: 构建小规模金标集，跟踪 Recall@K / MRR / nDCG。",
            "提示防注入: 检索片段进入生成前做注入过滤与来源标记。",
        ]
        if "RAG 与检索质量" in tracks or any(k in blob for k in ["rag", "retrieval", "search"]):
            return base
        return base[:4]


class LearningAnalystAgent:
    """Agent that orchestrates multiple skills for deep daily learning interpretation."""

    def __init__(self) -> None:
        self._trend_skill = TrendClusteringSkill()
        self._vendor_skill = VendorLandscapeSkill()
        self._priority_skill = ImprovementPrioritizationSkill()
        self._classic_rag_skill = ClassicRAGOptimizationSkill()

    @staticmethod
    def _safe_json(text: str) -> dict:
        cleaned = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL).strip()
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
        cleaned = re.sub(r",\s*([\]\}])", r"\1", cleaned)
        return json.loads(cleaned)

    @staticmethod
    def _build_fallback_interpretation(
        tracks: list[str],
        system_characteristics: list[str],
        vendor_view: str,
        recs: list[SkillRecommendation],
        issue_count: int,
        project_count: int,
        classic_rag_optimizations: list[str],
    ) -> AgentInterpretation:
        risks = [
            "多源学习信号已增长，但项目端与外部信号的执行闭环仍可能不足。",
            "若持续依赖单一路由策略，可能导致模型可用性或成本风险。",
        ]
        opportunities = [
            "可将多厂商动态转为 A/B 实验议题，缩短策略验证周期。",
            "可把学习结论映射到测试与观测指标，实现可验证改进。",
        ]
        plan = [
            "D1: 对齐当天学习轨道与系统模块映射表。",
            "D2: 从外部信号提炼 2 条可执行改进假设。",
            "D3: 将假设落地为 issue/todo，并标注验证指标。",
            "D4: 运行最小回归并记录质量变化。",
            "D5: 做多厂商同题对照并给出选型建议。",
            "D6: 复盘失败假设并更新学习策略。",
            "D7: 输出周总结与下周优先级。",
        ]
        summary = (
            f"系统特征聚焦于 {' / '.join(system_characteristics[:3] or ['AI-RAG 平台'])}；"
            f"学习轨道为 {' / '.join(tracks)}。{vendor_view}"
            f" 当前项目信号 issue={issue_count}, project={project_count}，建议将学习结论强制接入验证闭环。"
        )
        return AgentInterpretation(
            summary=summary,
            learning_tracks=tracks,
            system_characteristics=system_characteristics,
            key_risks=risks,
            opportunities=opportunities,
            seven_day_plan=plan,
            classic_rag_optimizations=classic_rag_optimizations,
            recommendations=recs,
        )

    @staticmethod
    async def _deep_interpret(prompt: str) -> dict[str, Any] | None:
        model = settings.ARK_MODEL
        base_url = settings.ARK_BASE_URL
        api_key = settings.ARK_API_KEY

        # Fallback path: if ARK key not set, try global OpenAI-compatible endpoint.
        if not api_key:
            api_key = settings.LLM_API_KEY or ""
            base_url = settings.LLM_BASE_URL or base_url

        if not api_key or not model:
            return None
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是HiveMind学习系统的首席架构分析师。"
                        "请基于系统特征和多源学习信号输出深度结构化解读，不要空话。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        return LearningAnalystAgent._safe_json(content)

    async def interpret(
        self,
        issues: list[dict],
        project_items: list[dict],
        external_signals: list[dict],
        system_characteristics: list[str],
    ) -> AgentInterpretation:
        signals = [SignalItem(**s) for s in external_signals if s.get("title")]
        issue_titles = [x.get("title", "") for x in issues]
        project_titles = [x.get("title", "") for x in project_items]

        tracks = self._trend_skill.run(signals)
        vendor_view = self._vendor_skill.run(signals)
        recs = self._priority_skill.run(issue_titles, project_titles, tracks)
        classic_rag_optimizations = self._classic_rag_skill.run(tracks, issue_titles)

        base_summary = (
            f"今日学习轨道: {' / '.join(tracks)}。"
            f"{vendor_view}"
            f" 项目端共观察到 {len(issue_titles)} 条 issue 信号与 {len(project_titles)} 条 project 信号。"
        )

        fallback = self._build_fallback_interpretation(
            tracks=tracks,
            system_characteristics=system_characteristics,
            vendor_view=vendor_view,
            recs=recs,
            issue_count=len(issue_titles),
            project_count=len(project_titles),
            classic_rag_optimizations=classic_rag_optimizations,
        )

        prompt = (
            "请输出JSON，字段必须包含：\n"
            "summary: 字符串，120-220字，聚焦系统特征+风险+动作\n"
            "system_characteristics: 字符串数组(3-6项)\n"
            "key_risks: 字符串数组(2-4项)\n"
            "opportunities: 字符串数组(2-4项)\n"
            "seven_day_plan: 字符串数组(7项，D1..D7)\n"
            "classic_rag_optimizations: 字符串数组(4-8项，强调传统有效手段，不追逐噱头)\n"
            "\\n上下文如下：\n"
            f"system_characteristics={system_characteristics}\n"
            f"learning_tracks={tracks}\n"
            f"vendor_landscape={vendor_view}\n"
            f"classic_rag_baseline={classic_rag_optimizations}\n"
            f"issue_titles={issue_titles[:20]}\n"
            f"project_titles={project_titles[:20]}\n"
            f"skill_recommendations={[r.model_dump() for r in recs]}\n"
            "要求：具体、可执行、避免泛化术语。"
        )

        # Deep model first (deepseek-v3-2-251201), then deterministic fallback.
        try:
            data = await self._deep_interpret(prompt)
            if not data:
                return fallback
            return AgentInterpretation(
                summary=data.get("summary", fallback.summary),
                learning_tracks=tracks,
                system_characteristics=data.get("system_characteristics", fallback.system_characteristics),
                key_risks=data.get("key_risks", fallback.key_risks),
                opportunities=data.get("opportunities", fallback.opportunities),
                seven_day_plan=data.get("seven_day_plan", fallback.seven_day_plan),
                classic_rag_optimizations=data.get("classic_rag_optimizations", fallback.classic_rag_optimizations),
                recommendations=recs,
            )
        except Exception:
            # Keep report generation robust if ARK is unavailable.
            return AgentInterpretation(
                summary=f"{base_summary}（deepseek-v3-2-251201不可用，已回退规则解读）",
                learning_tracks=fallback.learning_tracks,
                system_characteristics=fallback.system_characteristics,
                key_risks=fallback.key_risks,
                opportunities=fallback.opportunities,
                seven_day_plan=fallback.seven_day_plan,
                classic_rag_optimizations=fallback.classic_rag_optimizations,
                recommendations=fallback.recommendations,
            )
