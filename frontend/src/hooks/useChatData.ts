import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '../services/chatApi';

/**
 * 🛰️ [Architecture-Gate]: 业务服务端状态 (Server State)
 * 职责: 管理对话列表和对话详情的缓存与同步。
 * 策略: 剥离 Zustand store 中的异步逻辑，统一交由 React Query。
 */

/** 对话列表查询 */
export const useConversations = () => {
    return useQuery({
        queryKey: ['conversations'],
        queryFn: async () => {
            const res = await chatApi.getConversations();
            // Backend wraps lists in ApiResponse.ok([...]) → unwrap if present.
            const body = res.data as unknown;
            if (Array.isArray(body)) return body;
            if (body && typeof body === 'object' && Array.isArray((body as { data?: unknown }).data)) {
                return (body as { data: unknown[] }).data;
            }
            return [];
        },
    });
};

/** 对话详情查询 */
export const useConversationDetails = (id: string | null) => {
    return useQuery({
        queryKey: ['conversation', id],
        queryFn: async () => {
            if (!id) return null;
            const res = await chatApi.getConversation(id);
            // Robustly handle both wrapped (ApiResponse.ok(data)) and unwrapped responses
            const body = res.data as any;
            let messages: any[] = [];
            if (body && typeof body === 'object') {
                if (Array.isArray(body.messages)) {
                    messages = body.messages;
                } else if (body.data && Array.isArray(body.data.messages)) {
                    messages = body.data.messages;
                }
            }
            // 归一化后端消息格式
            // eslint-disable-next-line @typescript-eslint/no-explicit-any -- backend payload shape varies across providers
            return messages.map((m: any) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                created_at: m.created_at,
                rating: m.rating,
                metadata: m.metadata ? (typeof m.metadata === 'string' ? JSON.parse(m.metadata) : m.metadata) : {
                    prompt_tokens: m.prompt_tokens,
                    completion_tokens: m.completion_tokens,
                    total_tokens: m.total_tokens,
                    latency_ms: m.latency_ms,
                    is_cached: m.is_cached,
                    trace_data: m.trace_data
                }
            }));
        },
        enabled: !!id,
    });
};

/** 删除对话 */
export const useDeleteConversation = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: string) => chatApi.deleteConversation(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['conversations'] });
        },
    });
};

/** 提交反馈 */
export const useSubmitFeedback = () => {
    return useMutation({
        mutationFn: ({ messageId, rating }: { messageId: string, rating: number }) =>
            chatApi.submitFeedback(messageId, rating),
    });
};
