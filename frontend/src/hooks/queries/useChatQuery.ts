import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { chatApi, type ConversationItem, type ConversationDetail } from '../../services/chatApi';

/**
 * 🛰️ [FE-GOV-001]: 对话与会话管理 Hook (Standardized)
 */

export const CHAT_QUERY_KEYS = {
    CONVERSATIONS: ['conversations'] as const,
    CONVERSATION: (id: string) => ['conversation', id] as const,
};

/** 
 * 获取所有历史会话列表
 */
export function useConversationsQuery(options?: Partial<UseQueryOptions<ConversationItem[], Error>>) {
    return useQuery({
        queryKey: CHAT_QUERY_KEYS.CONVERSATIONS,
        queryFn: async () => {
            const res = await chatApi.getConversations();
            return res.data;
        },
        staleTime: 1000 * 60 * 2, // 2分钟缓存
        ...options as any
    });
}

/** 
 * 获取单个会话详情 (消息流)
 */
export function useConversationDetailQuery(id: string | null, options?: Partial<UseQueryOptions<ConversationDetail | null, Error>>) {
    return useQuery({
        queryKey: CHAT_QUERY_KEYS.CONVERSATION(id || 'none'),
        queryFn: async () => {
            if (!id) return null;
            const res = await chatApi.getConversation(id);
            return res.data;
        },
        enabled: !!id,
        ...options as any
    });
}

/** 
 * 删除会话 Mutation
 */
export function useDeleteConversationMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => chatApi.deleteConversation(id),
        onSuccess: () => {
            // 删除成功后使列表失效
            queryClient.invalidateQueries({ queryKey: CHAT_QUERY_KEYS.CONVERSATIONS });
        }
    });
}

/**
 * 提交反馈 Mutation
 */
export function useSubmitFeedbackMutation() {
    return useMutation({
        mutationFn: ({ messageId, rating, comment }: { messageId: string; rating: number; comment?: string }) => 
            chatApi.submitFeedback(messageId, rating, comment)
    });
}
