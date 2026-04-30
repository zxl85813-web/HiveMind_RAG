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

from sqlmodel import desc, select
from loguru import logger

from app.core.database import get_db_session
from app.core.tenant_context import get_current_tenant
from app.models.chat import Conversation, Message
from app.models.evaluation import BadCase
from app.schemas.chat import ChatMessage, ChatRequest, ConversationListItem


class ChatService:
    """对话服务 — 核心业务逻辑。"""

    @staticmethod
    async def create_conversation(user_id: str, title: str = "New Chat") -> Conversation:
        """创建新会话。"""
        async for session in get_db_session():
            conv = Conversation(user_id=user_id, title=title, tenant_id=get_current_tenant())
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            return conv
        return None  # Should not reach here

    @staticmethod
    async def get_conversations(user_id: str, limit: int = 20, offset: int = 0) -> list[ConversationListItem]:
        """获取用户的会话列表 (优化 N+1 查询)。"""
        from sqlalchemy import func
        tenant_id = get_current_tenant()
        async for session in get_db_session():
            # 1. Fetch conversations — tenant scoped
            stmt = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .where(Conversation.tenant_id == tenant_id)
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
            # We use a subquery to find the max(created_at) for each conversation
            subq = (
                select(Message.conversation_id, func.max(Message.created_at).label("max_created_at"))
                .where(Message.conversation_id.in_(conv_ids))
                .group_by(Message.conversation_id)
                .subquery()
            )
            
            msg_stmt = (
                select(Message)
                .join(subq, (Message.conversation_id == subq.c.conversation_id) & (Message.created_at == subq.c.max_created_at))
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
        return []

    @staticmethod
    async def get_conversation(conv_id: str) -> Conversation | None:
        """获取单个会话及其所有消息。"""
        tenant_id = get_current_tenant()
        async for session in get_db_session():
            statement = select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.tenant_id == tenant_id,
            )
            result = await session.exec(statement)
            conv = result.first()
            if conv:
                # 触发消息加载 (SQLModel Relationship)
                _ = conv.messages
            return conv

    @staticmethod
    async def delete_conversation(conv_id: str) -> bool:
        """删除会话及其关联消息。"""
        tenant_id = get_current_tenant()
        async for session in get_db_session():
            conv_statement = select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.tenant_id == tenant_id,
            )
            conv_result = await session.exec(conv_statement)
            conv = conv_result.first()
            if not conv:
                return False
            
            # 删除消息
            msg_statement = select(Message).where(Message.conversation_id == conv_id)
            msg_results = await session.exec(msg_statement)
            for m in msg_results.all():
                await session.delete(m)
            
            # 删除会话
            await session.delete(conv)
            await session.commit()
            return True
        return False

    @staticmethod
    async def record_feedback(msg_id: str, rating: int, text: str | None = None) -> bool:
        """Record user feedback (like/dislike) for a specific AI message."""
        from app.models.evaluation import EvaluationSet, EvaluationItem
        
        async for session in get_db_session():
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
                # 寻找本轮对话对应的 user question
                stmt_q = select(Message).where(Message.conversation_id == msg.conversation_id).where(Message.role == 'user').where(Message.created_at <= msg.created_at).order_by(Message.created_at.desc())
                user_q = (await session.exec(stmt_q)).first()
                if user_q:
                    existing_bc = (await session.exec(select(BadCase).where(BadCase.message_id == msg_id))).first()
                    if not existing_bc:
                        bad_case = BadCase(
                            message_id=msg_id,
                            question=user_q.content,
                            bad_answer=msg.content,
                            reason=text or "User disliked this answer",
                            status="pending"
                        )
                        session.add(bad_case)
                        logger.info(f"Automatically created BadCase entry for message {msg_id}")

            # 2. Positive Feedback -> Evaluation/Few-shot set (M2.1F)
            if rating == 1:
                # 寻找对应的 user question
                stmt_q = select(Message).where(Message.conversation_id == msg.conversation_id).where(Message.role == 'user').where(Message.created_at <= msg.created_at).order_by(Message.created_at.desc())
                user_q = (await session.exec(stmt_q)).first()
                if user_q:
                    # Find a "User-Gold" Evaluation Set or create one
                    set_stmt = select(EvaluationSet).where(EvaluationSet.name == "User-Gold Feedback Set")
                    eval_set = (await session.exec(set_stmt)).first()
                    
                    if not eval_set:
                        # Find first available KB to link this set to (Default strategy)
                        from app.models.knowledge import KnowledgeBase
                        kb_stmt = select(KnowledgeBase).limit(1)
                        kb = (await session.exec(kb_stmt)).first()
                        if kb:
                            eval_set = EvaluationSet(
                                kb_id=kb.id, 
                                name="User-Gold Feedback Set", 
                                description="High-quality RAG pairs verified by user 'Like' feedback."
                            )
                            session.add(eval_set)
                            await session.flush() # Get ID
                    
                    if eval_set:
                        # Check for duplicate
                        dup_stmt = select(EvaluationItem).where(EvaluationItem.set_id == eval_set.id, EvaluationItem.question == user_q.content)
                        if not (await session.exec(dup_stmt)).first():
                            eval_item = EvaluationItem(
                                set_id=eval_set.id,
                                question=user_q.content,
                                ground_truth=msg.content,
                                reference_context="Captured from Chat Feedback"
                            )
                            session.add(eval_item)
                            logger.info(f"✨ AI-First: Automatically promoted Liked Chat to EvaluationItem {eval_item.id}")

            await session.commit()
            logger.info(f"Feedback recorded for message {msg_id}: rating={rating}")
            return True
        return False

    @staticmethod
    async def chat_stream(request: ChatRequest, user_id: str) -> AsyncGenerator[str, None]:
        """
        核心流式对话生成器 — 使用 SwarmOrchestrator 进行智能编排与多级存储检索。
        P2: 集成语义缓存 (Semantic Cache) 与 Token 追踪。
        """
        from app.api.routes.agents import _swarm
        from app.services.cache_service import CacheService, TokenService
        from app.core.tracing import ChatTracer
        import time

        start_time = time.time()
        tracer = ChatTracer()
        conversation_id = request.conversation_id
        is_cached = False

        # 1. 如果没有会话ID，创建新会话
        if not conversation_id:
            conv = await ChatService.create_conversation(user_id, title=request.message[:20])
            conversation_id = conv.id
            yield f"data: {json.dumps({'type': 'session_created', 'id': conversation_id, 'title': conv.title})}\n\n"
        
        # 1.5 Record Client Events (Frontend Operation Logs)
        if request.client_events:
            for event in request.client_events:
                tracer.add_quick_step(
                    name=f"Client: {event.get('name', 'Interaction')}",
                    output=event.get("data", "No data"),
                    step_type="client",
                    metadata={"timestamp": event.get("timestamp")}
                )

        # 2 & 3. Save User Message & Load History (M6.4 Session Optimization)
        history = []
        async for session in get_db_session():
            user_msg = Message(conversation_id=conversation_id, role="user", content=request.message)
            session.add(user_msg)
            await session.commit()

            # Load history in same session
            stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at).limit(10)
            res = await session.exec(stmt)
            for m in res.all():
                if m.id == user_msg.id: # Skip current
                    continue
                if m.role == "user":
                    from langchain_core.messages import HumanMessage
                    history.append(HumanMessage(content=m.content))
                elif m.role == "assistant":
                    from langchain_core.messages import AIMessage
                    history.append(AIMessage(content=m.content))
            break

        # 4. Semantic Cache Lookup
        cache_step = tracer.start_step("Semantic Cache Check", "tool", input_data=request.message)
        cached = await CacheService.get_cached_response(request.message)
        if cached:
            is_cached = True
            cache_step.complete(output="Cache Hit", status="success")
            logger.info("🚀 Semantic Cache Hit! Skipping LLM Swarm.")
            yield f"data: {json.dumps({'type': 'status', 'content': '⚡ 语义缓存命中: 正在极速回复...'})}\n\n"
            response_content = cached["content"]
            # Stream the cached content to keep UI experience consistent
            # --- Phase 6: Batch Yielding (M6.3) ---
            batch_size = 30
            for i in range(0, len(response_content), batch_size):
                chunk = response_content[i:i + batch_size]
                yield f"data: {json.dumps({'type': 'content', 'delta': chunk, 'conversation_id': conversation_id, 'is_cached': True})}\n\n"
                await asyncio.sleep(0.01) # Faster than per-char but still has progress feel
        else:
            cache_step.complete(output="Cache Miss", status="info")
            # 5. Prepare Context
            context = {
                "user_id": user_id  # Inject user identity for Phase 7 KB Access Control
            }
            if request.knowledge_base_ids:
                context["knowledge_base_ids"] = request.knowledge_base_ids

            # 5.5 Load Security Policy for Outbound Filtering
            policy_rules = None
            async for session in get_db_session():
                from app.services.security_service import SecurityService
                policy = await SecurityService.get_active_policy(session)
                if policy and policy.rules_json:
                    policy_rules = json.loads(policy.rules_json)
                break 

            # 6. 调用 Swarm 编排器
            response_content = ""
            swarm_step = tracer.start_step("Swarm Orchestration", "agent", input_data=request.message)
            try:
                current_sub_step = None
                async for output in _swarm.invoke_stream(request.message, context=context, history=history, conversation_id=conversation_id):
                    # --- Thought Chain & Status Mapping ---
                    for node_name, updates in output.items():
                        if not isinstance(updates, dict):
                            continue
                            
                        # 1. Primary Thought Log (Architecture Internal)
                        if "thought_log" in updates and updates["thought_log"]:
                            yield f"data: {json.dumps({'type': 'status', 'content': updates['thought_log']})}\n\n"
                            
                        # 2. Legacy Status Updates
                        if "status_update" in updates and updates["status_update"]:
                            yield f"data: {json.dumps({'type': 'status', 'content': updates['status_update']})}\n\n"

                        # 3. Node Specific Mapping
                        if node_name == "retrieval":
                            ret_logs = updates.get("retrieval_trace", [])
                            ret_docs = updates.get("retrieved_docs", [])
                            tracer.add_quick_step(
                                "Memory Retrieval", 
                                "Searching Radar/Graph/Vector Store", 
                                "retrieval",
                                metadata={"logs": ret_logs, "docs": ret_docs} if (ret_logs or ret_docs) else None
                            )
                            yield f"data: {json.dumps({'type': 'status', 'content': '🔍 检索核心资产库中...' if not ret_docs else f'📚 找到 {len(ret_docs)} 相关条目'})}\n\n"
                        
                        if node_name == "supervisor":
                            next_agent = updates.get("next_step")
                            if next_agent and next_agent != "FINISH":
                                tracer.add_quick_step("Supervisor Decision", f"Handing over to {next_agent}", "agent")
                                # yield f"data: {json.dumps({'type': 'status', 'content': f'👨‍✈️ 编排决策: 由 {next_agent} 处理回复'})}\n\n" # Combined with thought_log now
                    
                    # --- Content Stream Handling ---
                    for node_name, updates in output.items():
                        if node_name not in ["retrieval", "supervisor", "reflection", "pre_processor"]:
                            if "messages" in updates:
                                raw_content = updates["messages"][-1].content
                                if policy_rules:
                                    from app.audit.security.engine import DesensitizationEngine
                                    content, _ = DesensitizationEngine.process_text(raw_content, policy_rules)
                                else:
                                    content = raw_content
                                
                                # --- AI-First Refinement: Clean up internal model tags (M2.1H) ---
                                import re
                                
                                # Detect and yield thinking content if model uses <think> or <thought> tags
                                # (Note: This is a simplified version; real-time extraction from partial chunks is harder)
                                thinking_match = re.search(r'<(think|thought)>(.*?)</\1>', content, re.DOTALL)
                                if thinking_match:
                                    think_content = thinking_match.group(2).strip()
                                    if think_content:
                                        yield f"data: {json.dumps({'type': 'status', 'content': f'🤔 思考: {think_content[:150]}...'})}\n\n"
                                
                                # Remove common leaked internal tags from models like DeepSeek (e.g., <|tool_calls_begin|>)
                                content = re.sub(r'<[\|｜].*?[\|｜]>', '', content)
                                content = content.replace('< | tool_calls_begin | >', '')
                                content = content.replace('< | tool_calls_end | >', '')
                                # Also strip the thinking tags for final display
                                content = re.sub(r'<(think|thought)>.*?</\1>', '', content, flags=re.DOTALL)
                                
                                # Skip if result is just empty tags or whitespace
                                if not content.strip():
                                    continue
                                
                                # --- Phase 6: Batch Yielding (M6.3) ---
                                batch_size = 15
                                for i in range(0, len(content), batch_size):
                                    chunk = content[i:i + batch_size]
                                    response_content += chunk
                                    yield f"data: {json.dumps({'type': 'content', 'delta': chunk, 'conversation_id': conversation_id})}\n\n"
                                    # Optimized delay for smooth typing (M6.3)
                                    await asyncio.sleep(0.005)

                swarm_step.complete(output="Generation Completed")
                # 6.5 Set Cache for future similar questions (only if it's a REAL answer, not a tool leak)
                if response_content and not any(tag in response_content for tag in ["tool_calls_begin", "tool_sep"]):
                    await CacheService.set_cached_response(request.message, response_content)

            except Exception as e:
                swarm_step.complete(output=str(e), status="error")
                logger.error(f"Swarm invocation failed: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Swarm Error: {str(e)}'})}\n\n"

        # 7. Generate Proactive Insight (AI-First)
        insight_step = tracer.start_step("Proactive Insight", "agent")
        try:
            from app.services.insight_service import InsightService
            # Ensure history is always included for context-aware insights
            full_history = "\n".join([m.content for m in history] + [request.message])
            insight = await InsightService.generate_session_insight(full_history, response_content)
            if insight:
                insight_step.complete(output=f"Generated {len(insight.actions)} actions")
                yield f"data: {json.dumps({'type': 'insight', 'data': insight.dict()})}\n\n"
            else:
                insight_step.complete(output="No insight generated")
        except Exception as e:
            insight_step.complete(output=str(e), status="error")
            logger.warning(f"Failed to generate session insight: {e}")

        # 8. Performance Metrics Calculation
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        p_tokens = TokenService.count_tokens(request.message)
        c_tokens = TokenService.count_tokens(response_content)
        total_tokens = p_tokens + c_tokens

        # 9. 保存 AI 最终回复与指标
        async for session in get_db_session():
            actions_json = None
            if 'insight' in locals() and insight:
                actions_json = json.dumps([a.dict() for a in insight.actions])
            
            ai_msg = Message(
                conversation_id=conversation_id, 
                role="assistant", 
                content=response_content,
                # P2 Metrics
                prompt_tokens=p_tokens if not is_cached else 0,
                completion_tokens=c_tokens if not is_cached else 0,
                total_tokens=total_tokens if not is_cached else 0,
                latency_ms=latency_ms,
                is_cached=is_cached,
                metadata_json=json.dumps({"actions": actions_json}) if actions_json else None,
                trace_data=tracer.get_trace_json()  # Save custom trace!
            )
            session.add(ai_msg)
            await session.commit()

        # 10. 结束信号
        yield f"data: {json.dumps({'type': 'done', 'latency_ms': latency_ms, 'is_cached': is_cached})}\n\n"
