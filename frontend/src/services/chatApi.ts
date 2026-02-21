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

const API_BASE = '/api/v1'; // Base is already handled by api.ts axios instance for non-SSE, but SSE uses fetchEventSource

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
        onSessionCreated?: (id: string, title: string) => void;
        onFinish?: () => void;
        onError?: (err: unknown) => void;
        controller?: AbortController;
    }) {
        const { message, conversationId, knowledgeBaseIds, onDelta, onStatus, onSessionCreated, onFinish, onError, controller } = params;

        // Use the baseURL from import.meta.env via a clean string construction
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

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
                }),
                signal: controller?.signal,

                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);

                        if (data.type === 'content') {
                            onDelta(data.delta);
                        } else if (data.type === 'status') {
                            onStatus?.(data.content);
                        } else if (data.type === 'session_created') {
                            onSessionCreated?.(data.id, data.title);
                        } else if (data.type === 'done') {
                            onFinish?.();
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
        return api.post('/learning/feedback', {
            message_id: messageId,
            rating,
            comment
        });
    }
};
