import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { chatApi, type ConversationItem, type ConversationDetail } from '../../services/chatApi';
import { baseline } from '../../core/BaselineProbe';
import { edgeEngine } from '../../core/LocalEdgeEngine';

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
            // 🛰️ [HMER Phase 2]: Local-First 影子策略步进
            baseline.mark('conversations-start');
            
            // 1. 尝试从 IndexedDB 秒取
            const localData = await edgeEngine.getAll('conversations');
            if (localData.length > 0) {
                 baseline.mark('local-hit');
                 baseline.measure('Local Store Hit (Phase 2)', 'conversations-start', 'local-hit');
                 // 这里我们虽然拿到了本地数据，但为了让 React Query 继续执行网络同步，
                 // 我们不直接 return，而是让 sync 在后台运行。
            }

            // 2. 发起远程同步
            try {
                const res = await chatApi.getConversations();
                const remoteData = res.data;

                // 3. 异步刷入本地影子库 (Fire and forget in background)
                void edgeEngine.batchPut('conversations', remoteData);

                baseline.mark('conversations-end');
                baseline.measure('Conversation List Sync (Remote)', 'conversations-start', 'conversations-end');
                
                return remoteData;
            } catch (err) {
                // 如果网络挂了，由于我们已经有了 localData，可以作为兜底返回
                if (localData.length > 0) return localData;
                throw err;
            }
        },
        placeholderData: [], // 开启占位符
        initialData: () => {
            // 这里有个更高级的技巧：如果已经有本地预取的缓存，可以直接注入 initialData
            return undefined; 
        },
        staleTime: 1000 * 30, // 缩短 staleTime 增加同步频率
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
            baseline.mark(`conversation-detail-start-${id}`);
            const res = await chatApi.getConversation(id);
            baseline.mark(`conversation-detail-end-${id}`);
            baseline.measure('Conversation Detail Fetch (Baseline)', `conversation-detail-start-${id}`, `conversation-detail-end-${id}`);
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
