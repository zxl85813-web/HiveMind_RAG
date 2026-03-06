import { fetchEventSource } from '@microsoft/fetch-event-source';
import api from './api';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
    metadata?: any;
}

export interface ConversationDetail {
    id: string;
    title: string;
    messages: ChatMessage[];
    created_at: string;
    updated_at: string;
}

export interface ConversationItem {
    id: string;
    title: string;
    last_message_preview: string;
    created_at: string;
    updated_at: string;
}

// Base is already handled by api.ts axios instance for non-SSE, but SSE uses fetchEventSource

export const chatApi = {
    /**
     * 发送流式对话请求 (SSE)
     */
    async streamChat(params: {
        message: string;
        conversationId?: string | null;
        knowledgeBaseIds?: string[];
        onDelta: (delta: string) => void;
        onStatus?: (status: string) => void;
        onInsight?: (data: any) => void;
        onSessionCreated?: (id: string, title: string) => void;
        onFinish?: (metrics?: { latency_ms?: number; is_cached?: boolean }) => void;
        clientEvents?: any[];
        onError?: (err: unknown) => void;
        controller?: AbortController;
    }) {
        const { message, conversationId, knowledgeBaseIds, clientEvents, onDelta, onStatus, onInsight, onSessionCreated, onFinish, onError, controller } = params;

        // Use the baseURL from import.meta.env via a clean string construction
        const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';

        try {
            await fetchEventSource(`${baseUrl}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Note: Auth header might be needed here if your SSE is protected
                },
                body: JSON.stringify({
                    message,
                    conversation_id: conversationId,
                    knowledge_base_ids: knowledgeBaseIds,
                    client_events: clientEvents
                }),
                signal: controller?.signal,

                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);

                        if (data.type === 'content') {
                            onDelta(data.delta);
                        } else if (data.type === 'status') {
                            onStatus?.(data.content);
                        } else if (data.type === 'insight') {
                            onInsight?.(data.data);
                        } else if (data.type === 'session_created') {
                            onSessionCreated?.(data.id, data.title);
                        } else if (data.type === 'done') {
                            onFinish?.({
                                latency_ms: data.latency_ms,
                                is_cached: data.is_cached
                            });
                        } else if (data.type === 'error') {
                            onError?.(new Error(data.message || data.content));
                        }
                    } catch (err) {
                        console.error('SSE parse error:', err);
                    }
                },

                onerror(err) {
                    console.error('SSE connection error:', err);
                    onError?.(err);
                    throw err; // 中断重试
                },
            });
        } catch (err) {
            if (onError) onError(err);
        }
    },

    /**
     * 获取会话列表
     */
    getConversations: () => {
        return api.get<ConversationItem[]>('/chat/conversations');
    },

    /**
     * 获取指定会话详情
     */
    getConversation: (id: string) => {
        return api.get<ConversationDetail>(`/chat/conversations/${id}`);
    },

    /**
     * 删除会话
     */
    deleteConversation: (id: string) => {
        return api.delete(`/chat/conversations/${id}`);
    },

    /**
     * 提交消息反馈
     */
    async submitFeedback(messageId: string, rating: number, comment?: string) {
        return api.post(`/chat/messages/${messageId}/feedback`, {
            rating,
            feedback_text: comment
        });
    }
};
