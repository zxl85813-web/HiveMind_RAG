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


from app.models.learning import TechDiscovery, TechSubscription

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
    Now backed by persistent DB storage (Phase 7 Hardening).
    """

    @staticmethod
    async def get_subscriptions() -> list[TechSubscription]:
        """Fetch all active learning subscriptions."""
        async with async_session_factory() as session:
            stmt = select(TechSubscription).where(TechSubscription.is_active == True)
            res = await session.execute(stmt)
            return list(res.scalars().all())

    @staticmethod
    async def add_subscription(topic: str) -> TechSubscription:
        """Add a new persistent sub."""
        async with async_session_factory() as session:
            sub = TechSubscription(topic=topic)
            session.add(sub)
            await session.commit()
            await session.refresh(sub)
            return sub

    @staticmethod
    async def record_feedback(message_id: str, rating: int, comment: str | None = None):
        """Record user feedback into the database."""
        async with async_session_factory() as session:
            stmt = select(Message).where(Message.id == message_id)
            res = await session.execute(stmt)
            message = res.scalars().one_or_none()
            if not message:
                logger.warning(f"Message {message_id} not found for feedback.")
                return

            message.rating = rating
            message.feedback_comment = comment
            session.add(message)
            await session.commit()
            logger.info(f"✅ Feedback recorded for message {message_id}: {rating}")

    @staticmethod
    async def learn_from_feedback(message_id: str):
        """
        L4 Learning: Convert a negative feedback case into a Cognitive Directive.
        """
        async with async_session_factory() as session:
            stmt = select(Message).where(Message.id == message_id)
            res = await session.execute(stmt)
            msg = res.scalars().one_or_none()
            if not msg or msg.rating != -1:
                return

            # Find the question (HumanMessage before this AIMessage)
            from app.models.chat import Conversation
            conv_stmt = select(Message).where(Message.conversation_id == msg.conversation_id).order_by(Message.created_at.desc())
            c_res = await session.execute(conv_stmt)
            msgs = c_res.scalars().all()
            
            question = ""
            for i, m in enumerate(msgs):
                if m.id == message_id and i + 1 < len(msgs):
                    question = msgs[i+1].content
                    break

            if not question:
                return

            # Trigger ExperienceLearner
            from app.models.evaluation import BadCase
            # Create a virtual BadCase for the learner
            case = BadCase(
                question=question,
                bad_answer=msg.content,
                reason=msg.feedback_comment or "User negative feedback"
            )
            session.add(case)
            await session.commit()
            await session.refresh(case)

            from app.services.evolution.experience_learner import experience_learner
            await experience_learner.learn_from_correction(session, case.id)
            logger.info(f"🧠 [Evolution] Learned from feedback on message {message_id}")

    @staticmethod
    async def learn_from_evaluation(report_id: str):
        """
        Automated Self-Improvement: Analyze failed items in an evaluation report.
        """
        from app.models.evaluation import EvaluationReport, BadCase
        from app.services.evolution.experience_learner import experience_learner

        async with async_session_factory() as session:
            report = await session.get(EvaluationReport, report_id)
            if not report: return

            # Find all bad cases linked to this report that aren't yet handled
            stmt = select(BadCase).where(BadCase.report_id == report_id, BadCase.status == "pending")
            res = await session.execute(stmt)
            cases = res.scalars().all()

            for case in cases:
                # If it has an expected answer (human corrected), learn deeply
                if case.expected_answer:
                    await experience_learner.learn_from_correction(session, case.id)
                    case.status = "reviewed"
                    session.add(case)
            
            await session.commit()

    @staticmethod
    async def delete_subscription(sub_id: str):
        async with async_session_factory() as session:
            sub = await session.get(TechSubscription, sub_id)
            if sub:
                await session.delete(sub)
                await session.commit()
                return True
            return False

    @staticmethod
    async def get_discoveries(limit: int = 50) -> list[TechDiscovery]:
        async with async_session_factory() as session:
            stmt = select(TechDiscovery).order_by(TechDiscovery.discovered_at.desc()).limit(limit)
            res = await session.execute(stmt)
            return list(res.scalars().all())

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _report_dir() -> Path:
        return LearningService._repo_root() / settings.SELF_LEARNING_REPORT_DIR

    @staticmethod
    def _read_heading(path: Path) -> str:
        try:
            with path.open(encoding="utf-8", errors="replace") as f:
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

    # ------------------------------------------------------------------
    # 实际爬取引擎 — Tier 2: GitHub Trending / Hacker News / ArXiv
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_github_trending() -> list[dict[str, str]]:
        """
        爬取 GitHub Trending（近 7 天 Stars 增长最快的仓库）。
        使用 GitHub Search API 模拟 Trending 效果：按语言过滤，按上周创建 + Star 数排序。
        """
        lang = settings.LEARNING_GITHUB_TRENDING_LANGUAGE
        limit = max(1, min(settings.LEARNING_GITHUB_TRENDING_LIMIT, 10))

        from datetime import timedelta

        since = (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
        query = f"language:{lang} created:>{since}"
        url = "https://api.github.com/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        try:
            async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
                resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.debug("GitHub trending fetch failed: status={}", resp.status_code)
                return []
            items = resp.json().get("items", [])
            return [
                {
                    "source": "github_trending",
                    "title": f"{item['full_name']} ⭐{item.get('stargazers_count', 0):,} — {item.get('description', '')[:80]}",
                    "url": item.get("html_url", ""),
                    "origin": item.get("full_name", ""),
                    "github_stars": str(item.get("stargazers_count", 0)),
                    "language": item.get("language") or lang,
                    "description": item.get("description") or "",
                }
                for item in items
            ]
        except Exception as e:
            logger.debug("GitHub trending exception: {}", e)
            return []

    @staticmethod
    async def _fetch_hacker_news() -> list[dict[str, str]]:
        """
        爬取 Hacker News 高分技术贴（使用 Algolia HN Search API）。
        只拉 AI/ML/Python/Agent 相关关键词，减少噪音。
        """
        min_score = settings.LEARNING_HN_MIN_SCORE
        limit = max(1, min(settings.LEARNING_HN_LIMIT, 10))
        tech_queries = [
            "LLM RAG agent vector",
            "python fastapi langchain",
            "artificial intelligence machine learning",
        ]

        signals: list[dict[str, str]] = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            for q in tech_queries:
                if len(signals) >= limit:
                    break
                try:
                    resp = await client.get(
                        "https://hn.algolia.com/api/v1/search",
                        params={
                            "query": q,
                            "tags": "story",
                            "numericFilters": f"points>{min_score}",
                            "hitsPerPage": limit,
                        },
                    )
                    if resp.status_code != 200:
                        continue
                    for hit in resp.json().get("hits", []):
                        title = hit.get("title") or ""
                        story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                        if title and not any(s["url"] == story_url for s in signals):
                            signals.append(
                                {
                                    "source": "hacker_news",
                                    "title": f"[HN] {title}",
                                    "url": story_url,
                                    "origin": "news.ycombinator.com",
                                    "hn_points": str(hit.get("points", 0)),
                                }
                            )
                except Exception as e:
                    logger.debug("HN fetch error for query '{}': {}", q, e)
        return signals[:limit]

    @staticmethod
    async def _fetch_arxiv() -> list[dict[str, str]]:
        """
        爬取 ArXiv 最新论文（使用官方 Atom Feed API）。
        按配置的分类拉取最新提交的论文。
        """
        categories = LearningService._split_csv(settings.LEARNING_ARXIV_CATEGORIES)
        max_results = max(1, min(settings.LEARNING_ARXIV_MAX_RESULTS, 20))
        if not categories:
            return []

        cat_query = " OR ".join(f"cat:{c}" for c in categories[:5])
        url = "https://export.arxiv.org/api/query"
        params = {
            "search_query": cat_query,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        _ATOM = "http://www.w3.org/2005/Atom"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.debug("ArXiv fetch failed: status={}", resp.status_code)
                return []

            root = ElementTree.fromstring(resp.text)
            entries = root.findall(f"{{{_ATOM}}}entry")
            signals: list[dict[str, str]] = []
            for entry in entries:
                title_el = entry.find(f"{{{_ATOM}}}title")
                id_el = entry.find(f"{{{_ATOM}}}id")
                summary_el = entry.find(f"{{{_ATOM}}}summary")
                title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
                link = (id_el.text or "").strip() if id_el is not None else ""
                abstract = (summary_el.text or "").strip()[:180].replace("\n", " ") if summary_el is not None else ""
                if title:
                    signals.append(
                        {
                            "source": "arxiv",
                            "title": f"[ArXiv] {title}",
                            "url": link,
                            "origin": "arxiv.org",
                            "abstract": abstract,
                        }
                    )
            return signals
        except Exception as e:
            logger.debug("ArXiv fetch exception: {}", e)
            return []

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

    # ------------------------------------------------------------------
    # 相关性评估模型 — LLM 评估新技术与项目栈的匹配度
    # ------------------------------------------------------------------

    @staticmethod
    async def assess_relevance(
        signals: list[dict[str, str]],
        tech_stack_context: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        使用 LLM 批量评估外部信号与当前项目技术栈的相关性。

        每条 signal 追加两个字段：
          - relevance_score  float  0.0 ~ 1.0
          - relevance_reason str    LLM 给出的简短理由（中文）

        低于 settings.LEARNING_RELEVANCE_MIN_SCORE 的条目仍返回，由调用方决定是否过滤。
        LLM 不可用时降级为全部赋予 0.5，保证流程不中断。
        """
        if not signals:
            return []

        stack = tech_stack_context or settings.LEARNING_TECH_STACK_CONTEXT

        # Build a numbered list for LLM context
        items_text = "\n".join(
            f"{i + 1}. {s.get('title', '')} (source={s.get('source', '')})" for i, s in enumerate(signals)
        )
        prompt = (
            f"你是一位技术架构师，负责评估外部技术资讯与当前项目技术栈的相关性。\n"
            f"当前项目技术栈关键词：{stack}\n\n"
            f"请为以下每条资讯评分（0.0=完全无关，1.0=高度相关），并给出一句中文理由。\n"
            f"严格按 JSON 数组输出，格式："
            '[{"index":1,"score":0.8,"reason":"..."}, ...]\n'
            "不要输出任何其他内容。\n\n"
            f"资讯列表：\n{items_text}"
        )

        scored: list[dict[str, Any]] = [dict(s) for s in signals]
        try:
            from openai import AsyncOpenAI

            llm_key = settings.OPENAI_API_KEY or settings.ARK_API_KEY
            llm_base = settings.OPENAI_BASE_URL if settings.OPENAI_API_KEY else settings.ARK_BASE_URL
            llm_model = settings.LLM_MODEL if hasattr(settings, "LLM_MODEL") else settings.ARK_MODEL

            client = AsyncOpenAI(api_key=llm_key, base_url=llm_base)
            response = await client.chat.completions.create(
                model=llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=512,
            )
            raw = (response.choices[0].message.content or "").strip()

            # Robustly extract JSON array from response
            import json as _json
            import re as _re

            match = _re.search(r"\[.*\]", raw, _re.DOTALL)
            if match:
                results = _json.loads(match.group())
                score_map: dict[int, tuple[float, str]] = {}
                for r in results:
                    idx = int(r.get("index", 0)) - 1
                    score_map[idx] = (float(r.get("score", 0.5)), r.get("reason", ""))
                for i, item in enumerate(scored):
                    s, reason = score_map.get(i, (0.5, ""))
                    item["relevance_score"] = round(s, 3)
                    item["relevance_reason"] = reason
                logger.debug("[assess_relevance] Scored {} signals via LLM.", len(scored))
                return scored
        except Exception as e:
            logger.warning("[assess_relevance] LLM scoring failed ({}), defaulting to 0.5.", e)

        # Fallback: neutral score
        for item in scored:
            item.setdefault("relevance_score", 0.5)
            item.setdefault("relevance_reason", "LLM 评分不可用")
        return scored

    @staticmethod
    async def run_external_crawl() -> list[TechDiscovery]:
        """
        定时爬取入口：拉取 GitHub Trending + HN + ArXiv，
        经相关性评估后存入 _discoveries 并返回高质量发现列表。
        """
        import uuid

        logger.info("[ExternalCrawl] Starting crawl cycle...")
        raw: list[dict[str, str]] = []
        raw += await LearningService._fetch_github_trending()
        raw += await LearningService._fetch_hacker_news()
        raw += await LearningService._fetch_arxiv()

        if not raw:
            logger.info("[ExternalCrawl] No signals fetched this cycle.")
            return []

        scored = await LearningService.assess_relevance(raw)
        min_score = settings.LEARNING_RELEVANCE_MIN_SCORE
        discoveries: list[TechDiscovery] = []
        for item in scored:
            score = item.get("relevance_score", 0.0)
            if score < min_score:
                continue
            source = item.get("source", "external")
            discoveries.append(
                TechDiscovery(
                    id=f"{source}_{uuid.uuid4().hex[:8]}",
                    title=item.get("title", ""),
                    summary=item.get("relevance_reason") or item.get("abstract") or item.get("description") or "",
                    url=item.get("url", ""),
                    category=(
                        "paper" if source == "arxiv"
                        else "tool" if source == "github_trending"
                        else "article"
                    ),
                    relevance_score=score,
                    discovered_at=datetime.now(UTC),
                )
            )

        # Prepend new discoveries to DB
        async with async_session_factory() as session:
            for disc in discoveries:
                # Deduplicate by URL
                stmt = select(TechDiscovery).where(TechDiscovery.url == disc.url)
                check = await session.execute(stmt)
                if not check.scalars().one_or_none():
                    session.add(disc)
            
            await session.commit()

        logger.info(
            "[ExternalCrawl] Cycle complete: {} raw signals → {} stored discoveries (min_score={}).",
            len(raw),
            len(discoveries),
            min_score,
        )
        return discoveries

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

    @classmethod
    async def ingest_discovery(cls, discovery_id: str):
        """
        [M7.2] 将技术发现内化为智体群落的语义记忆 (SwarmKnowledge)。
        """
        from app.models.agents import SwarmKnowledge
        from app.agents.memory import SharedMemoryManager
        
        db = SessionLocal()
        try:
            stmt = select(TechDiscovery).where(TechDiscovery.id == discovery_id)
            discovery = db.exec(stmt).first()
            if not discovery:
                return None
            
            # 1. 构造语义知识节点
            knowledge_key = f"tech:{discovery.category}:{discovery.title[:50].lower().replace(' ', '_')}"
            knowledge = SwarmKnowledge(
                key=knowledge_key,
                content=f"Discovery: {discovery.title}\n\nSummary: {discovery.summary}\n\nSource: {discovery.url}",
                details={
                    "original_discovery_id": discovery.id,
                    "relevance_score": discovery.relevance_score,
                    "ingested_at": datetime.utcnow().isoformat()
                }
            )
            
            # 2. 保存至共享记忆系统
            memory = SharedMemoryManager()
            await memory.save_knowledge(knowledge)
            
            # 3. 更新状态
            discovery.status = "ingested"
            db.add(discovery)
            db.commit()
            
            logger.info(f"💾 Ingested tech discovery into semantic memory: {knowledge_key}")
            return knowledge
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    @classmethod
    def read_report_content(cls, report_path: str) -> str:
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
        # 实际爬取引擎 (2.4): GitHub Trending / HN / ArXiv
        crawl_github = await LearningService._fetch_github_trending()
        crawl_hn = await LearningService._fetch_hacker_news()
        crawl_arxiv = await LearningService._fetch_arxiv()
        external_signals = ai_feed_signals + github_repo_signals + x_watchlist + crawl_github + crawl_hn + crawl_arxiv

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
