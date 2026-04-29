/**
 * Chat 相关辅助类型 — 把 `types/index.ts` 中内联在 `ChatMessage.metadata` 里的
 * 匿名对象提取为独立可复用类型。
 */
import type { Source, AgentTraceStep } from './index';

/** Chat 消息元数据（与 ChatMessage.metadata 同形）*/
export interface ChatMessageMetadata {
    model?: string;
    sources?: Source[];
    agent_trace?: AgentTraceStep[];
    /** 当前页面上下文 */
    context_page?: string;
    /** 流式过程中的状态文案 */
    statuses?: string[];
    /** 性能 / 缓存 */
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    latency_ms?: number;
    is_cached?: boolean;
    trace_data?: string;
}

/** 提交给后端的客户端事件（与 ClientEvent 同形，但显式契约导出）*/
export interface ClientEventPayload {
    name: string;
    data: string;
    timestamp: string;
}
