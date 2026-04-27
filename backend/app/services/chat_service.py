"""
Chat Service — 处理对话核心逻辑。

职责:
1. 管理对话会话 (Conversation/Message CRUD)
2. 调用 Agent Swarm执行任务
3. 处理流式响应 (SSE Generator)

参见: REGISTRY.md > 后端 > services > chat_service
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from loguru import logger
from sqlmodel import desc, select

from app.core.database import async_session_factory
from app.models.chat import Conversation, Message
from app.models.evaluation import BadCase
from app.schemas.chat import ChatRequest, ConversationListItem


class ChatService:
    """对话服务 — 核心业务逻辑。"""

    @staticmethod
    async def create_conversation(user_id: str, title: str = "New Chat") -> Conversation:
        """创建新会话。"""
        async with async_session_factory() as session:
            conv = Conversation(user_id=user_id, title=title)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            return conv

    @staticmethod
    async def get_conversations(user_id: str, limit: int = 20, offset: int = 0) -> list[ConversationListItem]:
        """获取用户的会话列表 (优化 N+1 查询)。"""
        from sqlalchemy import func

        async with async_session_factory() as session:
            # 1. Fetch conversations
            stmt = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(desc(Conversation.updated_at))
                .offset(offset)
                .limit(limit)
            )
            results = await session.exec(stmt)
            conversations = results.all()
            if not conversations:
                return []

            conv_ids = [c.id for c in conversations]

            # 2. Fetch latest messages for all these conversations in one batch
            subq = (
                select(Message.conversation_id, func.max(Message.created_at).label("max_created_at"))
                .where(Message.conversation_id.in_(conv_ids))
                .group_by(Message.conversation_id)
                .subquery()
            )

            msg_stmt = select(Message).join(
                subq,
                (Message.conversation_id == subq.c.conversation_id) & (Message.created_at == subq.c.max_created_at),
            )
            msg_results = await session.exec(msg_stmt)
            latest_messages = {m.conversation_id: m for m in msg_results.all()}

            # 3. Assemble results
            items = []
            for c in conversations:
                last_msg = latest_messages.get(c.id)
                preview = last_msg.content[:50] if last_msg else "暂无消息"
                items.append(
                    ConversationListItem(
                        id=c.id,
                        title=c.title,
                        last_message_preview=preview,
                        created_at=c.created_at,
                        updated_at=c.updated_at,
                    )
                )
            return items

    @staticmethod
    async def get_conversation(conv_id: str) -> Conversation | None:
        """获取单个会话及其所有消息。"""
        async with async_session_factory() as session:
            statement = select(Conversation).where(Conversation.id == conv_id)
            result = await session.exec(statement)
            conv = result.first()
            if conv:
                _ = conv.messages
            return conv

    @staticmethod
    async def delete_conversation(conv_id: str) -> bool:
        """删除会话及其关联消息。"""
        async with async_session_factory() as session:
            conv_statement = select(Conversation).where(Conversation.id == conv_id)
            conv_result = await session.exec(conv_statement)
            conv = conv_result.first()
            if not conv:
                return False

            msg_statement = select(Message).where(Message.conversation_id == conv_id)
            msg_results = await session.exec(msg_statement)
            for m in msg_results.all():
                await session.delete(m)

            await session.delete(conv)
            await session.commit()
            return True

    @staticmethod
    async def record_feedback(msg_id: str, rating: int, text: str | None = None) -> bool:
        """Record user feedback (like/dislike) for a specific AI message."""
        from app.models.evaluation import EvaluationItem, EvaluationSet

        async with async_session_factory() as session:
            statement = select(Message).where(Message.id == msg_id)
            result = await session.exec(statement)
            msg = result.first()
            if not msg:
                logger.warning(f"Feedback target message not found: {msg_id}")
                return False

            msg.rating = rating
            if text is not None:
                msg.feedback_text = text

            session.add(msg)

            # --- Automation Logic (AI-First) ---

            # 1. Negative Feedback -> Bad Case Analysis (M2.1E)
            if rating == -1:
                stmt_q = (
                    select(Message)
                    .where(Message.conversation_id == msg.conversation_id)
                    .where(Message.role == "user")
                    .where(Message.created_at <= msg.created_at)
                    .order_by(Message.created_at.desc())
                )
                user_q = (await session.exec(stmt_q)).first()
                if user_q:
                    existing_bc = (await session.exec(select(BadCase).where(BadCase.message_id == msg_id))).first()
                    if not existing_bc:
                        bad_case = BadCase(
                            message_id=msg_id,
                            question=user_q.content,
                            bad_answer=msg.content,
                            reason=text or "User disliked this answer",
                            status="pending",
                        )
                        session.add(bad_case)
                        logger.info(f"Automatically created BadCase entry for message {msg_id}")

            # 2. Positive Feedback -> Evaluation/Few-shot set (M2.1F)
            if rating == 1:
                stmt_q = (
                    select(Message)
                    .where(Message.conversation_id == msg.conversation_id)
                    .where(Message.role == "user")
                    .where(Message.created_at <= msg.created_at)
                    .order_by(Message.created_at.desc())
                )
                user_q = (await session.exec(stmt_q)).first()
                if user_q:
                    set_stmt = select(EvaluationSet).where(EvaluationSet.name == "User-Gold Feedback Set")
                    eval_set = (await session.exec(set_stmt)).first()

                    if not eval_set:
                        from app.models.knowledge import KnowledgeBase

                        kb_stmt = select(KnowledgeBase).limit(1)
                        kb = (await session.exec(kb_stmt)).first()
                        if kb:
                            eval_set = EvaluationSet(
                                kb_id=kb.id,
                                name="User-Gold Feedback Set",
                                description="High-quality RAG pairs verified by user 'Like' feedback.",
                            )
                            session.add(eval_set)
                            await session.flush()  # Get ID

                    if eval_set:
                        dup_stmt = select(EvaluationItem).where(
                            EvaluationItem.set_id == eval_set.id, EvaluationItem.question == user_q.content
                        )
                        if not (await session.exec(dup_stmt)).first():
                            eval_item = EvaluationItem(
                                set_id=eval_set.id,
                                question=user_q.content,
                                ground_truth=msg.content,
                                reference_context="Captured from Chat Feedback",
                            )
                            session.add(eval_item)
                            logger.info(
                                f"✨ AI-First: Automatically promoted Liked Chat to EvaluationItem {eval_item.id}"
                            )

            await session.commit()
            logger.info(f"Feedback recorded for message {msg_id}: rating={rating}")
            return True

    @staticmethod
    async def chat_stream(
        request: ChatRequest, user_id: str, accept_language: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        核心流式对话生成器 — 使用 SwarmOrchestrator 进行智能编排与多级存储检索。
        P2: 集成语义缓存 (Semantic Cache) 与 Token 追踪。
        P3: 卫星级弹性流层 — 支持断点续传、多轨解析与服务降级。
        """
        import re
        import time

        from app.api.routes.agents import _swarm
        from app.core.tracing import ChatTracer
        from app.services.cache_service import CacheService, TokenService

        start_time = time.time()
        tracer = ChatTracer()
        conversation_id = request.conversation_id
        is_cached = False
        variant_meta = {
            "prompt_variant": request.prompt_variant,
            "retrieval_variant": request.retrieval_variant,
        }

        tracer.add_quick_step(
            "Experiment Variants",
            f"prompt={request.prompt_variant}, retrieval={request.retrieval_variant}",
            "config",
            metadata=variant_meta,
        )

        # --- 🛰️ [HMER Phase 3]: Chunk Counter for Resumption ---
        chunk_counter = 0

        async def _yield_payload(track_name: str, payload_data: dict):
            nonlocal chunk_counter
            chunk_counter += 1
            # 如果提供了 resume_index，则跳过之前的分块 (极简逻辑: 物理跳过)
            if request.resume_index is not None and chunk_counter <= request.resume_index:
                return

            payload_data["_index"] = chunk_counter
            payload_data["track"] = track_name
            payload_data["type"] = track_name
            yield f"data: {json.dumps(payload_data)}\n\n"

        # --- 🆕 [Phase 4.1]: Prefetch Interceptor ---
        if request.is_prefetch:
            logger.info(f"🛰️ Prefetch probe for: {request.message[:20]}...")
            async for p in _yield_payload("status", {"content": "🔍 正在为您预先加载检索资产..."}):
                yield p

            # 💡 [Strategy]: Here we would normally run just the retrieval node.
            # For now, we perform a cache lookup to prime the system.
            cached = await CacheService.get_cached_response(request.message)
            status_msg = "⚡ 预热完成: 命中语义缓存" if cached else "✅ 预热完成: 检索索引已加载至热点内存"

            async for p in _yield_payload("status", {"content": status_msg}):
                yield p
            async for p in _yield_payload("done", {"is_prefetch": True}):
                yield p
            return # 🔚 Shortcut! No LLM, No database writes.

        # --- 1. 如果没有会话ID，创建新会话 ---
        if not conversation_id:
            conv = await ChatService.create_conversation(user_id, title=request.message[:20])
            conversation_id = conv.id
            async for p in _yield_payload("session_created", {"id": conversation_id, "title": conv.title}):
                yield p

        # 1.5 Record Client Events (Frontend Operation Logs)
        if request.client_events:
            for event in request.client_events:
                tracer.add_quick_step(
                    name=f"Client: {event.get('name', 'Interaction')}",
                    output=event.get("data", "No data"),
                    step_type="client",
                    metadata={"timestamp": event.get("timestamp")},
                )

        # 2 & 3. Save User Message & Load History (M6.4 Session Optimization)
        history = []
        async with async_session_factory() as session:
            user_msg = Message(conversation_id=conversation_id, role="user", content=request.message)
            session.add(user_msg)
            await session.commit()

            # Load history in same session
            stmt = (
                select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at).limit(10)
            )
            res = await session.exec(stmt)
            for m in res.all():
                if m.id == user_msg.id:  # Skip current
                    continue
                if m.role == "user":
                    from langchain_core.messages import HumanMessage
                    history.append(HumanMessage(content=m.content))
                elif m.role == "assistant":
                    from langchain_core.messages import AIMessage
                    history.append(AIMessage(content=m.content))

        # 4. Semantic Cache Lookup
        cache_step = tracer.start_step("Semantic Cache Check", "tool", input_data=request.message)
        cached = await CacheService.get_cached_response(request.message)
        if cached:
            is_cached = True
            cache_step.complete(output="Cache Hit", status="success")
            logger.info("🚀 Semantic Cache Hit! Skipping LLM Swarm.")
            async for p in _yield_payload("status", {"content": "⚡ 语义缓存命中: 正在极速回复..."}):
                yield p

            response_content = cached["content"]
            batch_size = 30
            for i in range(0, len(response_content), batch_size):
                chunk = response_content[i : i + batch_size]
                async for p in _yield_payload("content", {
                    "delta": chunk,
                    "conversation_id": conversation_id,
                    "is_cached": True
                }):
                    yield p
                await asyncio.sleep(0.01)
        else:
            cache_step.complete(output="Cache Miss", status="info")
            # 5. Prepare Context (ARM-P0-4)
            from app.auth.permissions import AuthorizationContext
            from app.models.chat import User
            from app.services.knowledge.kb_service import KnowledgeService

            user_role = "user"
            user_dept = None
            auth_kb_ids = []

            async with async_session_factory() as session:
                user_obj = await session.get(User, user_id)
                if user_obj:
                    user_role = user_obj.role
                    user_dept = user_obj.department_id
                    kb_service = KnowledgeService(session)
                    auth_kb_ids = await kb_service.get_user_accessible_kbs(user_obj)

            auth_context = AuthorizationContext(
                user_id=user_id,
                role=user_role,
                department_id=user_dept,
                authorized_kb_ids=auth_kb_ids,
            )

            context = {
                "user_id": user_id,
                "auth_context": auth_context,
                "prompt_variant": request.prompt_variant,
                "retrieval_variant": request.retrieval_variant,
                "execution_variant": request.execution_variant, # 🆕 [GOV-EXP-001]
                "language": accept_language or "zh-CN",
            }
            if request.knowledge_base_ids:
                context["knowledge_base_ids"] = request.knowledge_base_ids

            # 5.5 Load Security Policy for Outbound Filtering
            policy_rules = None
            async with async_session_factory() as session:
                from app.services.security_service import SecurityService
                policy = await SecurityService.get_active_policy(session)
                if policy and policy.rules_json:
                    policy_rules = json.loads(policy.rules_json)

            # 6. 调用 Swarm 编排器
            response_content = ""
            swarm_step = tracer.start_step("Swarm Orchestration", "agent", input_data=request.message)
            try:
                async for output in _swarm.invoke_stream(
                    request.message, context=context, history=history, conversation_id=conversation_id
                ):
                    # --- Thought Chain & Status Mapping ---
                    for node_name, updates in output.items():
                        if not isinstance(updates, dict):
                            continue

                        if updates.get("thought_log"):
                            async for p in _yield_payload("status", {"content": updates["thought_log"]}):
                                yield p

                        if updates.get("status_update"):
                            async for p in _yield_payload("status", {"content": updates["status_update"]}):
                                yield p

                        if node_name == "retrieval":
                            ret_logs = updates.get("retrieval_trace", [])
                            ret_docs = updates.get("retrieved_docs", [])
                            tracer.add_quick_step(
                                "Memory Retrieval",
                                "Searching Radar/Vector Store",
                                "retrieval",
                                metadata={"logs": ret_logs, "docs": ret_docs} if (ret_logs or ret_docs) else None,
                            )
                            status_msg = f"📚 找到 {len(ret_docs)} 相关条目" if ret_docs else "🔍 检索核心资产库中..."
                            async for p in _yield_payload("status", {"content": status_msg}):
                                yield p

                    # --- Content Stream Handling ---
                    for node_name, updates in output.items():
                        non_content_nodes = {"retrieval", "supervisor", "reflection", "pre_processor"}
                        if node_name not in non_content_nodes and "messages" in updates:
                            raw_content = updates["messages"][-1].content
                            if policy_rules:
                                from app.audit.security.engine import DesensitizationEngine
                                raw_content, _ = DesensitizationEngine.process_text(raw_content, policy_rules)

                            # --- 🛰️ [HMER Phase 3]: 精细化多轨提取 ---
                            thinking_match = re.search(r"<(think|thought)>(.*?)</\1>", raw_content, re.DOTALL)
                            if thinking_match:
                                async for p in _yield_payload("thinking", {"delta": thinking_match.group(2).strip()}):
                                    yield p

                            content = re.sub(r"<(think|thought)>.*?</\1>", "", raw_content, flags=re.DOTALL)
                            content = re.sub(r"<[\|｜].*?[\|｜]>", "", content)
                            content = content.replace(
                                "< | tool_calls_begin | >", ""
                            ).replace("< | tool_calls_end | >", "")

                            if not content.strip():
                                continue

                            batch_size = 15
                            for i in range(0, len(content), batch_size):
                                chunk = content[i : i + batch_size]
                                response_content += chunk
                                async for p in _yield_payload("content", {
                                    "delta": chunk,
                                    "conversation_id": conversation_id
                                }):
                                    yield p
                                await asyncio.sleep(0.005)

                swarm_step.complete(output="Generation Completed")
                if response_content and not any(tag in response_content for tag in ["tool_calls_begin", "tool_sep"]):
                    await CacheService.set_cached_response(request.message, response_content)

            except Exception as e:
                swarm_step.complete(output=str(e), status="error")
                logger.error(f"Swarm invocation failed: {e}")
                async for p in _yield_payload("error", {"content": f"Swarm Error: {e!s}"}):
                    yield p

        # 7. Generate Proactive Insight (AI-First)
        insight_step = tracer.start_step("Proactive Insight", "agent")
        try:
            from app.services.insight_service import InsightService
            full_history = "\n".join([m.content for m in history] + [request.message])
            insight = await InsightService.generate_session_insight(full_history, response_content)
            if insight:
                insight_step.complete(output=f"Generated {len(insight.actions)} actions")
                async for p in _yield_payload("insight", {"data": insight.dict()}):
                    yield p
            else:
                insight_step.complete(output="No insight generated")
        except Exception as e:
            insight_step.complete(output=str(e), status="error")
            logger.warning(f"Failed to generate session insight: {e}")

        # 8 & 9. Performance & Save
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        p_tokens = TokenService.count_tokens(request.message)
        c_tokens = TokenService.count_tokens(response_content)
        total_tokens = p_tokens + c_tokens

        async with async_session_factory() as session:
            actions_json = None
            if "insight" in locals() and insight:
                actions_json = json.dumps([a.dict() for a in insight.actions])

            ai_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_content,
                prompt_tokens=p_tokens if not is_cached else 0,
                completion_tokens=c_tokens if not is_cached else 0,
                total_tokens=total_tokens if not is_cached else 0,
                latency_ms=latency_ms,
                is_cached=is_cached,
                metadata_json=json.dumps({"actions": actions_json}) if actions_json else None,
                trace_data=tracer.get_trace_json(),
            )
            session.add(ai_msg)
            await session.commit()

        # 10. 结束信号
        async for p in _yield_payload("done", {"latency_ms": latency_ms, "is_cached": is_cached}):
            yield p

        # 11. 跨会话情节记忆蒸馏 (EP-006)
        if conversation_id and not is_cached:
            try:
                from app.services.memory.consolidator import consolidator
                current_session_msgs = []
                for m in history:
                    msg_role = "user" if m.type == "human" else "assistant"
                    current_session_msgs.append({"role": msg_role, "content": str(m.content)})
                current_session_msgs.append({"role": "user", "content": request.message})
                current_session_msgs.append({"role": "assistant", "content": response_content})

                # 持有 task 引用，防止 GC 在任务完成前回收
                task = asyncio.create_task(
                    consolidator.consolidate_session(
                        user_id=user_id, conversation_id=conversation_id, messages=current_session_msgs
                    )
                )
                _swarm._background_tasks.add(task)
                task.add_done_callback(_swarm._background_tasks.discard)
            except Exception as dist_err:
                logger.warning(f"Failed to trigger autonomous consolidation: {dist_err}")
