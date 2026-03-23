import { useQuery, useMutation, useQueryClient, QueryClient } from '@tanstack/react-query';
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

// --- Fetchers (Shared for Queries and Prefetching) ---

export const conversationFetcher = async () => {
    // 🛰️ [HMER Phase 2]: Local-First 影子策略步进
    baseline.mark('conversations-start');
    
    // 1. 尝试从 IndexedDB 秒取
    const localData = await edgeEngine.getAll('conversations');
    if (localData.length > 0) {
         baseline.mark('local-hit');
         baseline.measure('Local Store Hit (Phase 2)', 'conversations-start', 'local-hit');
    }

    // 2. 发起远程同步
    try {
        const res = await chatApi.getConversations();
        const remoteData = res.data;

        // 3. 异步刷入本地影子库
        void edgeEngine.batchPut('conversations', remoteData);

        baseline.mark('conversations-end');
        baseline.measure('Conversation List Sync (Remote)', 'conversations-start', 'conversations-end');
        
        return remoteData;
    } catch (err) {
        if (localData.length > 0) return localData;
        throw err;
    }
};

export const conversationDetailFetcher = (id: string) => async () => {
    baseline.mark(`conversation-detail-prefetch-start-${id}`);
    const res = await chatApi.getConversation(id);
    baseline.mark(`conversation-detail-prefetch-end-${id}`);
    baseline.measure('Conversation Detail Fetch (Phase 4)', `conversation-detail-prefetch-start-${id}`, `conversation-detail-prefetch-end-${id}`);
    return res.data;
};

// --- Queries ---

/** 
 * 获取所有历史会话列表
 */
export function useConversationsQuery(options?: Partial<UseQueryOptions<ConversationItem[], Error>>) {
    return useQuery({
        queryKey: CHAT_QUERY_KEYS.CONVERSATIONS,
        queryFn: conversationFetcher,
        placeholderData: [],
        staleTime: 1000 * 30,
        ...options as any
    });
}

/** 
 * 获取单个会话详情 (消息流)
 */
export function useConversationDetailQuery(id: string | null, options?: Partial<UseQueryOptions<ConversationDetail | null, Error>>) {
    return useQuery({
        queryKey: CHAT_QUERY_KEYS.CONVERSATION(id || 'none'),
        queryFn: id ? conversationDetailFetcher(id) : () => null,
        enabled: !!id,
        ...options as any
    });
}

/** 
 * 🛠️ [Phase 4] Prefetching Logic
 * 手动预热特定会话
 */
export async function prefetchConversation(queryClient: QueryClient, id: string) {
    await queryClient.prefetchQuery({
        queryKey: CHAT_QUERY_KEYS.CONVERSATION(id),
        queryFn: conversationDetailFetcher(id),
        staleTime: 1000 * 60 * 5, // 预热数据在 5 分钟内视为新鲜
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
