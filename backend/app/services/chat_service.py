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

from app.core.database import get_db_session
from app.models.chat import Conversation, Message
from app.schemas.chat import ChatRequest, ConversationListItem


class ChatService:
    """对话服务 — 核心业务逻辑。"""

    @staticmethod
    async def create_conversation(user_id: str, title: str = "New Chat") -> Conversation:
        """创建新会话。"""
        async for session in get_db_session():
            conv = Conversation(user_id=user_id, title=title)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            return conv
        return None  # Should not reach here

    @staticmethod
    async def get_conversations(user_id: str, limit: int = 20, offset: int = 0) -> list[ConversationListItem]:
        """获取用户的会话列表。"""
        async for session in get_db_session():
            statement = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(desc(Conversation.updated_at))
                .offset(offset)
                .limit(limit)
            )
            results = await session.exec(statement)
            conversations = results.all()

            items = []
            for c in conversations:
                # 获取最后一条消息作为预览
                msg_statement = (
                    select(Message)
                    .where(Message.conversation_id == c.id)
                    .order_by(desc(Message.created_at))
                    .limit(1)
                )
                msg_result = await session.exec(msg_statement)
                last_msg = msg_result.first()
                
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
        async for session in get_db_session():
            statement = select(Conversation).where(Conversation.id == conv_id)
            result = await session.exec(statement)
            conv = result.first()
            if conv:
                # 触发消息加载 (SQLModel Relationship)
                _ = conv.messages
            return conv

    @staticmethod
    async def delete_conversation(conv_id: str) -> bool:
        """删除会话及其关联消息。"""
        async for session in get_db_session():
            conv_statement = select(Conversation).where(Conversation.id == conv_id)
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
    async def chat_stream(request: ChatRequest, user_id: str) -> AsyncGenerator[str, None]:
        """
        核心流式对话生成器。

        Yields:
            SSE 格式数据: data: <json_string>\n\n
        """
        conversation_id = request.conversation_id

        # 1. 如果没有会话ID，创建新会话
        if not conversation_id:
            conv = await ChatService.create_conversation(user_id, title=request.message[:20])
            conversation_id = conv.id
            yield f"data: {json.dumps({'type': 'session_created', 'id': conversation_id, 'title': conv.title})}\n\n"

        # 2. 保存用户消息
        async for session in get_db_session():
            user_msg = Message(conversation_id=conversation_id, role="user", content=request.message)
            session.add(user_msg)
            await session.commit()

        # 3. Multi-tier Memory Routing (Radar + Vector)
        context_str = ""
        try:
            from app.core.llm import get_llm_service
            from app.services.memory.tier.abstract_index import abstract_index
            llm = get_llm_service()

            # --- Stage 1: Radar (Tier 1 Memory) ---
            # Fast extraction of intent tags
            radar_prompt = f"""
            Extract 1-3 searchable keywords (tags) from this query. 
            Return ONLY a JSON array of strings. Query: "{request.message}"
            """
            tags = []
            try:
                tags_json = await llm.chat_complete([{"role": "user", "content": radar_prompt}], json_mode=True)
                tags_data = json.loads(tags_json)
                if isinstance(tags_data, dict):
                    # Sometimes models wrap array in dict
                    tags = tags_data.get("tags", list(tags_data.values())[0])
                elif isinstance(tags_data, list):
                    tags = tags_data
            except Exception as e:
                pass
            
            radar_hits = []
            if tags and isinstance(tags, list):
                # Hit the memory memory!
                radar_hits = abstract_index.route_query(tags=tags, limit=3)
            
            if radar_hits:
                yield f"data: {json.dumps({'type': 'status', 'content': f'⚡ 雷达定位到 {len(radar_hits)} 个相关记忆 (Tags: {tags})'})}\n\n"
                context_str += "--- HOT MEMORY (Abstracts) ---\n"
                for hit in radar_hits:
                    context_str += f"- [{hit['date']}] {hit['title']} (Type: {hit['type']})\n"
                context_str += "\n"

            # --- Stage 1.5: Graph Neighborhood (Tier 2 Memory) ---
            from app.services.memory.tier.graph_index import graph_index
            if tags and isinstance(tags, list):
                neighbor_hits = graph_index.get_neighborhood(tags)
                if neighbor_hits:
                    yield f"data: {json.dumps({'type': 'status', 'content': f'🕸️ 图谱扩展了 {len(neighbor_hits)} 条关联上下文'})}\n\n"
                    context_str += "--- GLOBAL CONTEXT (Graph Neighborhood) ---\n"
                    context_str += "\n".join([f"- {n}" for n in neighbor_hits])
                    context_str += "\n\n"

            # --- Stage 2: Deep Vector Retrieval (Tier 3 Memory) ---
            from app.services.retrieval import get_retrieval_service
            retriever = get_retrieval_service()
            
            docs = await retriever.retrieve(request.message, collection_names=["default"], top_k=2)
            
            if docs:
                context_str += "--- DEEP CONTEXT ---\n"
                context_str += "\n".join([f"- {d.page_content}" for d in docs])
                if not radar_hits:
                    yield f"data: {json.dumps({'type': 'status', 'content': f'🔍 检索到 {len(docs)} 条相关上下文'})}\n\n"
                    
        except Exception as e:
            yield f"data: {json.dumps({'type': 'status', 'content': f'⚠️ 记忆检索异常: {e}'})}\n\n"

        # 4. LLM Generation
        from app.core.llm import get_llm_service
        llm = get_llm_service()
        
        system_prompt = "You are HiveMind, an AI Assistant. Answer concisely and helpfully."
        if context_str:
            system_prompt += f"\n\n## Context\n{context_str}\n\n## Instruction\nAnswer based on context if relevant."
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]

        response_content = ""
        try:
            async for delta in llm.stream_chat(messages):
                response_content += delta
                chunk = {"type": "content", "delta": delta, "conversation_id": conversation_id}
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # 5. 保存 AI 回复
        async for session in get_db_session():
            ai_msg = Message(conversation_id=conversation_id, role="assistant", content=response_content)
            session.add(ai_msg)
            await session.commit()

        # 6. 结束信号
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
