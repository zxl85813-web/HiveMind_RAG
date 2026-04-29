/**
 * Chat SSE Event Types — 与后端 `app.services.chat_service` 保持同步。
 *
 * SSE 不在 OpenAPI 描述范围内，所以手工定义一组判别联合 (discriminated union)。
 * 后端事件源 ↔ 前端 onmessage 处理在 `services/chatApi.ts`。
 *
 * @see backend/app/services/chat_service.py — 12 处 yield 事件
 * @see backend/app/services/insight_service.py — SwarmInsight schema
 */
import type { AIAction } from './index';

/** 后端 SwarmInsight 模型镜像 */
export interface SwarmInsight {
    summary: string;
    thought: string;
    actions: AIAction[];
}

/** 流式增量 token */
export interface SSEContentEvent {
    type: 'content';
    delta: string;
    conversation_id?: string;
    is_cached?: boolean;
}

/** 阶段性状态文案（思考、检索进度、Agent 切换提示等）*/
export interface SSEStatusEvent {
    type: 'status';
    content: string;
}

/** 会话首次创建（后端分配 ID）*/
export interface SSESessionCreatedEvent {
    type: 'session_created';
    id: string;
    title: string;
}

/** AI 主动洞察（在末轮发送）*/
export interface SSEInsightEvent {
    type: 'insight';
    data: SwarmInsight;
}

/** 流结束 + 性能/缓存指标 */
export interface SSEDoneEvent {
    type: 'done';
    latency_ms?: number;
    is_cached?: boolean;
}

/** 错误事件（业务错误，连接错误走 onerror）*/
export interface SSEErrorEvent {
    type: 'error';
    message?: string;
    content?: string;
}

/** 后端可能产生的所有 SSE 事件 */
export type ChatSSEEvent =
    | SSEContentEvent
    | SSEStatusEvent
    | SSESessionCreatedEvent
    | SSEInsightEvent
    | SSEDoneEvent
    | SSEErrorEvent;

/** 流结束时回调获得的指标摘要 */
export interface ChatStreamMetrics {
    latency_ms?: number;
    is_cached?: boolean;
}
