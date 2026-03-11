from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from loguru import logger
from pydantic import BaseModel
from sqlmodel import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.chat import Message
from app.services.learning_agentic import LearningAnalystAgent
from app.services.memory.memory_service import MemoryService


class Subscription(BaseModel):
    id: str
    topic: str
    is_active: bool = True
    created_at: datetime = datetime.now()


class TechDiscovery(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    category: str
    relevance_score: float
    discovered_at: datetime = datetime.now()


class LearningSuggestion(BaseModel):
    title: str
    reason: str
    action: str


class DailyLearningRun(BaseModel):
    report_date: str
    report_path: str
    local_materials_count: int
    github_project_items_count: int
    github_issues_count: int
    external_signals_count: int
    agent_summary: str
    learning_tracks: list[str]
    key_risks: list[str]
    opportunities: list[str]
    seven_day_plan: list[str]
    classic_rag_optimizations: list[str]
    suggestions: list[LearningSuggestion]


class LearningService:
    """
    Self-improving AI System and External Learning coordinator.
    """

    _mock_subscriptions: ClassVar[list[dict]] = [
        {"id": "sub_1", "topic": "LangChain", "is_active": True, "created_at": datetime.now()},
        {"id": "sub_2", "topic": "React 19", "is_active": True, "created_at": datetime.now()},
    ]

    _mock_discoveries: ClassVar[list[dict]] = [
        {
            "id": "disc_1",
            "title": "GPT-5 Architecture Leak?",
            "summary": "关于最新大模型架构的传闻分析，涉及多模态集成细节。",
            "url": "https://example.com/gpt5",
            "category": "paper",
            "relevance_score": 0.95,
            "discovered_at": datetime.now(),
        },
        {
            "id": "disc_2",
            "title": "HiveMind v2.0 Released",
            "summary": "HiveMind 框架发布重大更新，支持分布式 Agent 协同。",
            "url": "https://github.com/hivemind/core",
            "category": "tool",
            "relevance_score": 0.88,
            "discovered_at": datetime.now(),
        },
    ]

    @staticmethod
    async def get_subscriptions():
        return LearningService._mock_subscriptions

    @staticmethod
    async def add_subscription(topic: str):
        import uuid

        new_sub = {"id": f"sub_{uuid.uuid4().hex[:6]}", "topic": topic, "is_active": True, "created_at": datetime.now()}
        LearningService._mock_subscriptions.append(new_sub)
        return new_sub

    @staticmethod
    async def delete_subscription(sub_id: str):
        LearningService._mock_subscriptions = [s for s in LearningService._mock_subscriptions if s["id"] != sub_id]
        return True

    @staticmethod
    async def get_discoveries():
        return LearningService._mock_discoveries

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _report_dir() -> Path:
        return LearningService._repo_root() / settings.SELF_LEARNING_REPORT_DIR

    @staticmethod
    def _read_heading(path: Path) -> str:
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("#"):
                        return line.strip().lstrip("#").strip()
        except Exception as e:
            logger.warning("Failed to read heading from {}: {}", path, e)
        return path.name

    @staticmethod
    def _collect_local_materials() -> list[dict[str, str]]:
        repo_root = LearningService._repo_root()
        key_docs = [
            repo_root / "docs" / "SYSTEM_OVERVIEW.md",
            repo_root / "docs" / "architecture.md",
            repo_root / "docs" / "AGENT_GOVERNANCE.md",
            repo_root / "docs" / "DATA_GOVERNANCE.md",
            repo_root / "docs" / "DEV_GOVERNANCE.md",
            repo_root / "docs" / "LEARNING_PATH.md",
            repo_root / "docs" / "guides" / "collaboration_and_delivery_playbook.md",
        ]

        materials: list[dict[str, str]] = []
        for doc in key_docs:
            if not doc.exists():
                continue
            rel = doc.relative_to(repo_root).as_posix()
            materials.append({"path": rel, "title": LearningService._read_heading(doc)})
        return materials

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        return [part.strip() for part in value.split(",") if part.strip()]

    @staticmethod
    async def _fetch_ai_company_feed_signals() -> list[dict[str, str]]:
        feeds = LearningService._split_csv(settings.SELF_LEARNING_AI_FEEDS)
        if not feeds:
            return []

        headers = {"User-Agent": "HiveMindLearningBot/1.0"}
        signals: list[dict[str, str]] = []
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            for feed_url in feeds[:10]:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code != 200:
                        continue

                    root = ElementTree.fromstring(resp.text)
                    channel = root.find("channel")
                    item = None
                    if channel is not None:
                        item = channel.find("item")
                    if item is None:
                        # Atom fallback
                        item = root.find("{http://www.w3.org/2005/Atom}entry")

                    if item is None:
                        continue

                    title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or ""
                    link = item.findtext("link") or ""
                    if not link:
                        atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                        if atom_link is not None:
                            link = atom_link.attrib.get("href", "")

                    if title:
                        signals.append(
                            {
                                "source": "ai_company_feed",
                                "title": title.strip(),
                                "url": link.strip(),
                                "origin": urlparse(feed_url).netloc,
                            }
                        )
                except Exception as e:
                    logger.debug("Feed fetch failed for {}: {}", feed_url, e)
                    continue

        return signals

    @staticmethod
    async def _fetch_github_watch_repo_signals() -> list[dict[str, str]]:
        watch_repos = LearningService._split_csv(settings.SELF_LEARNING_GITHUB_WATCH_REPOS)
        if not watch_repos:
            return []

        headers = {"Accept": "application/vnd.github+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        signals: list[dict[str, str]] = []
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            for full_name in watch_repos[:15]:
                if "/" not in full_name:
                    continue
                try:
                    rel_url = f"https://api.github.com/repos/{full_name}/releases?per_page=1"
                    resp = await client.get(rel_url)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    if not data:
                        continue
                    latest = data[0]
                    title = latest.get("name") or latest.get("tag_name") or "latest release"
                    signals.append(
                        {
                            "source": "github_release",
                            "title": f"{full_name}: {title}",
                            "url": latest.get("html_url", ""),
                            "origin": full_name,
                        }
                    )
                except Exception as e:
                    logger.debug("GitHub watch repo fetch failed for {}: {}", full_name, e)
                    continue
        return signals

    @staticmethod
    def _build_x_watchlist() -> list[dict[str, str]]:
        accounts = LearningService._split_csv(settings.SELF_LEARNING_X_ACCOUNTS)
        return [
            {
                "source": "x_watchlist",
                "title": f"@{acc} 动态追踪",
                "url": f"https://x.com/{acc}",
                "origin": acc,
            }
            for acc in accounts[:20]
        ]

    @staticmethod
    async def _fetch_repo_issues() -> list[dict[str, Any]]:
        if not settings.GITHUB_TOKEN:
            return []

        owner = settings.GITHUB_REPO_OWNER
        repo = settings.GITHUB_REPO_NAME
        limit = max(1, settings.SELF_LEARNING_ISSUE_LIMIT)
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        params = {"state": "open", "per_page": limit, "sort": "updated", "direction": "desc"}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                logger.warning("Failed to fetch GitHub issues: status={} body={}", resp.status_code, resp.text[:200])
                return []
            data = resp.json()
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("html_url", ""),
                    "labels": [label.get("name", "") for label in item.get("labels", [])],
                }
                for item in data
                if "pull_request" not in item
            ]
        except Exception as e:
            logger.warning("Error fetching GitHub issues: {}", e)
            return []

    @staticmethod
    async def _fetch_project_items() -> list[dict[str, str]]:
        if not settings.GITHUB_TOKEN:
            return []
        if not settings.GITHUB_PROJECT_OWNER or settings.GITHUB_PROJECT_NUMBER <= 0:
            return []

        token = settings.GITHUB_TOKEN
        owner = settings.GITHUB_PROJECT_OWNER
        number = settings.GITHUB_PROJECT_NUMBER
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        query_tpl = """
        query($owner: String!, $number: Int!) {
          %s(login: $owner) {
            projectV2(number: $number) {
              title
              items(first: 20) {
                nodes {
                  content {
                    ... on Issue { title url }
                    ... on PullRequest { title url }
                    ... on DraftIssue { title }
                  }
                }
              }
            }
          }
        }
        """

        async def run_query(owner_type: str) -> list[dict[str, str]]:
            payload = {
                "query": query_tpl % owner_type,
                "variables": {"owner": owner, "number": number},
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post("https://api.github.com/graphql", headers=headers, json=payload)
            if resp.status_code != 200:
                return []
            body = resp.json()
            if body.get("errors"):
                return []
            container = body.get("data", {}).get(owner_type)
            if not container or not container.get("projectV2"):
                return []
            nodes = container["projectV2"].get("items", {}).get("nodes", [])
            results: list[dict[str, str]] = []
            for node in nodes:
                content = node.get("content") or {}
                title = content.get("title", "")
                if not title:
                    continue
                results.append({"title": title, "url": content.get("url", "")})
            return results

        try:
            org_items = await run_query("organization")
            if org_items:
                return org_items
            return await run_query("user")
        except Exception as e:
            logger.warning("Error fetching GitHub project items: {}", e)
            return []

    @staticmethod
    def _build_suggestions(
        issues: list[dict[str, Any]],
        project_items: list[dict[str, str]],
        local_materials: list[dict[str, str]],
        external_signals: list[dict[str, str]],
    ) -> list[LearningSuggestion]:
        text_blob = " ".join(
            [issue.get("title", "") for issue in issues]
            + [item.get("title", "") for item in project_items]
            + [signal.get("title", "") for signal in external_signals]
        ).lower()
        labels = [label.lower() for issue in issues for label in issue.get("labels", [])]

        suggestions: list[LearningSuggestion] = []

        if any(k in text_blob for k in ["test", "coverage", "regression"]) or "qa" in labels:
            suggestions.append(
                LearningSuggestion(
                    title="建立每日回归学习卡片",
                    reason="GitHub 项目中存在测试/回归相关信号，说明质量风险持续存在。",
                    action="把当天新增改动映射到最小回归用例，沉淀到 docs/learning/daily 的 Testing Checklist。",
                )
            )

        if any(k in text_blob for k in ["perf", "latency", "slow", "timeout", "memory"]):
            suggestions.append(
                LearningSuggestion(
                    title="增加性能专项学习主题",
                    reason="Issue/Project 出现性能与延迟关键词。",
                    action="每天抽取 1 个慢链路案例，记录瓶颈、指标和下一步优化假设。",
                )
            )

        if len(local_materials) < 5:
            suggestions.append(
                LearningSuggestion(
                    title="补齐系统核心文档覆盖",
                    reason="当前纳入每日学习的系统文档数量不足。",
                    action="优先补充 SYSTEM_OVERVIEW、architecture、治理三件套到学习清单。",
                )
            )

        if not external_signals:
            suggestions.append(
                LearningSuggestion(
                    title="补齐外部学习源配置",
                    reason="当前未获取到任何外部学习信号，学习内容可能单一。",
                    action="检查 GITHUB_TOKEN 与 SELF_LEARNING_AI_FEEDS / SELF_LEARNING_GITHUB_WATCH_REPOS 配置。",
                )
            )

        if "openai" in text_blob or "anthropic" in text_blob or "deepmind" in text_blob or "qwen" in text_blob:
            suggestions.append(
                LearningSuggestion(
                    title="建立多厂商对比学习卡",
                    reason="学习信号已覆盖多个 AI 厂商，适合做横向比较。",
                    action="每天选 1 个主题，对比 OpenAI/Anthropic/Google/Meta/阿里通义 的方案差异并记录可落地点。",
                )
            )

        if not suggestions:
            suggestions.append(
                LearningSuggestion(
                    title="执行稳定节奏学习闭环",
                    reason="当前项目未暴露高强度风险关键词，适合持续改进。",
                    action=(
                        "每日固定输出三段内容：系统知识点、GitHub 项目变化、可执行改进建议；"
                        "并在下个工作日追踪建议是否落地。"
                    ),
                )
            )

        return suggestions

    @staticmethod
    def _render_markdown(
        report_date: str,
        local_materials: list[dict[str, str]],
        project_items: list[dict[str, str]],
        issues: list[dict[str, Any]],
        external_signals: list[dict[str, str]],
        x_watchlist: list[dict[str, str]],
        agent_summary: str,
        learning_tracks: list[str],
        system_characteristics: list[str],
        key_risks: list[str],
        opportunities: list[str],
        seven_day_plan: list[str],
        classic_rag_optimizations: list[str],
        suggestions: list[LearningSuggestion],
    ) -> str:
        lines: list[str] = []
        lines.append(f"# Self Learning Report - {report_date}")
        lines.append("")
        lines.append("## 今日系统学习")
        lines.append("")
        if local_materials:
            for item in local_materials:
                lines.append(f"- `{item['path']}`: {item['title']}")
        else:
            lines.append("- 未读取到系统文档，请检查 docs 路径配置。")

        lines.append("")
        lines.append("## GitHub Project 变化")
        lines.append("")
        if project_items:
            for item in project_items[:10]:
                if item.get("url"):
                    lines.append(f"- [{item['title']}]({item['url']})")
                else:
                    lines.append(f"- {item['title']}")
        else:
            lines.append("- 未拉取到 Project 条目（可能未配置项目号或权限）。")

        lines.append("")
        lines.append("## GitHub Issues 信号")
        lines.append("")
        if issues:
            for issue in issues[:10]:
                title = issue.get("title", "")
                url = issue.get("url", "")
                if url:
                    lines.append(f"- [{title}]({url})")
                else:
                    lines.append(f"- {title}")
        else:
            lines.append("- 未拉取到 Issue 数据（可能未配置 token）。")

        lines.append("")
        lines.append("## 多元外部学习信号（X + AI 大厂 + 重点开源）")
        lines.append("")
        if external_signals:
            for signal in external_signals[:12]:
                title = signal.get("title", "")
                url = signal.get("url", "")
                source = signal.get("source", "external")
                if url:
                    lines.append(f"- [{title}]({url}) (`{source}`)")
                else:
                    lines.append(f"- {title} (`{source}`)")
        else:
            lines.append("- 未拉取到外部信号，建议检查 token 和 feed 配置。")

        lines.append("")
        lines.append("## X 关注清单")
        lines.append("")
        for item in x_watchlist[:10]:
            lines.append(f"- [{item['title']}]({item['url']})")

        lines.append("")
        lines.append("## Agent+Skill 深度解读")
        lines.append("")
        lines.append(f"- 解读结论: {agent_summary}")
        lines.append("- 系统特征:")
        for c in system_characteristics[:6]:
            lines.append(f"  - {c}")
        lines.append("- 学习轨道:")
        for track in learning_tracks:
            lines.append(f"  - {track}")

        lines.append("")
        lines.append("## 关键风险")
        lines.append("")
        for r in key_risks[:5]:
            lines.append(f"- {r}")

        lines.append("")
        lines.append("## 改进机会")
        lines.append("")
        for o in opportunities[:5]:
            lines.append(f"- {o}")

        lines.append("")
        lines.append("## 7日行动路线")
        lines.append("")
        for step in seven_day_plan[:7]:
            lines.append(f"- {step}")

        lines.append("")
        lines.append("## 传统RAG优化抓手")
        lines.append("")
        for item in classic_rag_optimizations[:8]:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## 系统改进建议")
        lines.append("")
        for idx, suggestion in enumerate(suggestions, start=1):
            lines.append(f"{idx}. {suggestion.title}")
            lines.append(f"   - 原因: {suggestion.reason}")
            lines.append(f"   - 行动: {suggestion.action}")

        lines.append("")
        lines.append("## 给系统使用者的学习指引")
        lines.append("")
        lines.append("- 先读`今日系统学习`中的前 2 条文档，再看当前 Project 变化。")
        lines.append("- 选择 1 条改进建议，转成 TODO/Issue，并在次日回看执行结果。")
        lines.append("- 从`多元外部学习信号`中任选 1 条，与本系统方案做差异对照。")
        lines.append("- 如果你是新用户，优先阅读 SYSTEM_OVERVIEW 和 LEARNING_PATH。")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def read_report_content(report_path: str) -> str:
        report_dir = LearningService._report_dir().resolve()
        target = (LearningService._repo_root() / report_path).resolve()
        # Safety check: prevent path traversal and enforce report directory boundary.
        if report_dir not in target.parents and target != report_dir:
            raise ValueError("Invalid report path")
        if not target.exists():
            raise FileNotFoundError(report_path)
        return target.read_text(encoding="utf-8")

    @staticmethod
    async def run_daily_learning_cycle() -> DailyLearningRun:
        """Run one daily self-learning cycle and persist a user-facing markdown report."""
        report_date = datetime.now(UTC).date().isoformat()
        local_materials = LearningService._collect_local_materials()
        project_items = await LearningService._fetch_project_items()
        issues = await LearningService._fetch_repo_issues()
        x_watchlist = LearningService._build_x_watchlist()
        ai_feed_signals = await LearningService._fetch_ai_company_feed_signals()
        github_repo_signals = await LearningService._fetch_github_watch_repo_signals()
        external_signals = ai_feed_signals + github_repo_signals + x_watchlist

        analyst = LearningAnalystAgent()
        system_characteristics = [item["title"] for item in local_materials]
        interpretation = await analyst.interpret(
            issues=issues,
            project_items=project_items,
            external_signals=external_signals,
            system_characteristics=system_characteristics,
        )

        skill_suggestions = [
            LearningSuggestion(title=r.title, reason=r.rationale, action=f"[{r.priority}] {r.action}")
            for r in interpretation.recommendations
        ]

        suggestions = LearningService._build_suggestions(issues, project_items, local_materials, external_signals)
        suggestions = skill_suggestions + suggestions

        report_text = LearningService._render_markdown(
            report_date,
            local_materials,
            project_items,
            issues,
            external_signals,
            x_watchlist,
            interpretation.summary,
            interpretation.learning_tracks,
            interpretation.system_characteristics,
            interpretation.key_risks,
            interpretation.opportunities,
            interpretation.seven_day_plan,
            interpretation.classic_rag_optimizations,
            suggestions,
        )
        report_dir = LearningService._report_dir()
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"{report_date}.md"
        report_file.write_text(report_text, encoding="utf-8")

        repo_root = LearningService._repo_root()
        rel_report_path = report_file.relative_to(repo_root).as_posix()
        logger.info("Daily self-learning report generated: {}", rel_report_path)

        return DailyLearningRun(
            report_date=report_date,
            report_path=rel_report_path,
            local_materials_count=len(local_materials),
            github_project_items_count=len(project_items),
            github_issues_count=len(issues),
            external_signals_count=len(external_signals),
            agent_summary=interpretation.summary,
            learning_tracks=interpretation.learning_tracks,
            key_risks=interpretation.key_risks,
            opportunities=interpretation.opportunities,
            seven_day_plan=interpretation.seven_day_plan,
            classic_rag_optimizations=interpretation.classic_rag_optimizations,
            suggestions=suggestions,
        )

    @staticmethod
    async def record_feedback(message_id: str, rating: int, comment: str | None = None):
        """Save raw feedback to DB."""
        async with async_session_factory() as session:
            msg = await session.get(Message, message_id)
            if msg:
                msg.rating = rating
                msg.feedback_text = comment
                session.add(msg)
                await session.commit()
                logger.info(f"Feedback recorded for msg {message_id}: {rating}")

    @staticmethod
    async def learn_from_feedback(message_id: str):
        """
        The Core Loop: Reflection & Knowledge Distillation.
        """
        async with async_session_factory() as session:
            ai_msg = await session.get(Message, message_id)
            if not ai_msg or not ai_msg.conversation_id:
                return

            # Get User Prompt (Previous message)
            # Simplification: Assume previous msg is user prompt
            query = (
                select(Message)
                .where(Message.conversation_id == ai_msg.conversation_id, Message.created_at < ai_msg.created_at)
                .order_by(Message.created_at.desc())
                .limit(1)
            )

            result = await session.exec(query)
            user_msg = result.first()

            if not user_msg:
                logger.warning("No context found for feedback analysis.")
                return

            # 1. Construct Reflection Prompt
            reflection_prompt = (
                "--- CONTEXT ---\n"
                f"User Query: {user_msg.content}\n"
                f"Your Response: {ai_msg.content}\n"
                f"User Feedback: {'POSITIVE' if ai_msg.rating > 0 else 'NEGATIVE'}"
                f" ({ai_msg.feedback_text or 'No comment'})\n"
            )

            # 2. Call LLM for Reflection (Mocked for now)
            # In production: response = await LLM.generate(reflection_prompt)
            reflection = await LearningService._mock_reflection(ai_msg.rating, user_msg.content)
            logger.debug("Reflection prompt built ({} chars)", len(reflection_prompt))

            # 3. Store Knowledge
            mem_service = MemoryService(user_id="system_learner")  # System-level memory
            await mem_service.add_memory(
                content=reflection,
                metadata={"type": "prompt_insight", "rating": ai_msg.rating, "source_msg": message_id},
            )

            logger.info(f"🧠 System Learned: {reflection[:50]}...")

    @staticmethod
    async def _mock_reflection(rating: int, query: str) -> str:
        """
        Mock LLM reflection logic.
        Reflect on WHY the response was good/bad.
        """
        if rating > 0:
            return (
                f"[SUCCESS PATTERN] When user asks about '{query[:10]}...',"
                " providing a step-by-step breakdown works well."
                " The structured format was appreciated."
            )
        else:
            return (
                f"[FAILURE ANALYSIS] User was unhappy with query '{query[:10]}...'."
                " Possible cause: The response was too verbose or lacked"
                " specific code examples. Action: Be more concise next time."
            )
