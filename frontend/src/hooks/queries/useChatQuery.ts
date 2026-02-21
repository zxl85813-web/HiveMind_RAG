import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import type { ConversationListItem } from '../../types';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { chatApi as _chatApi } from '../../services/chatApi'; // TODO: 用 chatApi 替换内联 mock

// Query Keys 常量化
export const QUERY_KEYS = {
    CONVERSATIONS: 'conversations',
    CONVERSATION: (id: string) => ['conversation', id],
};

// 获取会话列表 Hook
export function useConversationsQuery(options?: UseQueryOptions<ConversationListItem[], Error>) {
    return useQuery({
        queryKey: [QUERY_KEYS.CONVERSATIONS],
        queryFn: async () => {
            // 模拟 API 调用，实际替换为 chatApi.getConversations() 
            return [];
        },
        ...options
    });
}

// 创建会话 Mutation Hook
export function useCreateConversationMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (title: string) => {
            // 模拟 API 调用，实际替换为 chatApi.createConversation(title)
            return { id: Date.now().toString(), title };
        },
        onSuccess: () => {
            // 创建成功后，刷新列表 Query
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.CONVERSATIONS] });
        }
    });
}
