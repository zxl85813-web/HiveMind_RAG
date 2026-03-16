import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeApi, type CreateKnowledgeBaseParams } from '../../services/knowledgeApi';
import type { KnowledgeBase } from '../../types';

/**
 * 🛰️ [FE-GOV-001]: Knowledge Base 数据流管理 Hook
 * 
 * 职责: 统一管理知识库相关的 Server State，提供缓存、自动刷新与乐观更新基础。
 */

export const KNOWLEDGE_KEYS = {
    ALL: ['knowledge-bases'] as const,
    DETAIL: (id: string) => ['knowledge-base', id] as const,
    DOCUMENTS: (kbId: string) => ['knowledge-base', kbId, 'documents'] as const,
    GRAPH: (kbId: string) => ['knowledge-base', kbId, 'graph'] as const,
};

// --- Queries ---

/** 获取知识库列表 */
export function useKnowledgeBases() {
    return useQuery({
        queryKey: KNOWLEDGE_KEYS.ALL,
        queryFn: async () => {
            const res = await knowledgeApi.listKBs();
            return res.data.data;
        },
        staleTime: 1000 * 60 * 5, // 5分钟内数据视为新鲜
    });
}

/** 获取特定知识库详情 */
export function useKnowledgeBase(id: string | null) {
    return useQuery({
        queryKey: KNOWLEDGE_KEYS.DETAIL(id || 'none'),
        queryFn: async () => {
            if (!id) return null;
            const res = await knowledgeApi.getKB(id);
            return res.data.data;
        },
        enabled: !!id,
    });
}

/** 获取知识库文档列表 */
export function useKBDocuments(kbId: string | null) {
    return useQuery({
        queryKey: KNOWLEDGE_KEYS.DOCUMENTS(kbId || 'none'),
        queryFn: async () => {
            if (!kbId) return [];
            const res = await knowledgeApi.listDocsInKB(kbId);
            return res.data; // 注意: 部分接口返回 data 字段，部分直接返回数组，按实际 service 返回调整
        },
        enabled: !!kbId,
    });
}

// --- Mutations ---

/** 创建知识库 */
export function useCreateKBMutation() {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: (params: CreateKnowledgeBaseParams) => knowledgeApi.createKB(params),
        onSuccess: () => {
            // 创建成功后，强制刷新列表
            queryClient.invalidateQueries({ queryKey: KNOWLEDGE_KEYS.ALL });
        }
    });
}

/** 关联文档到知识库 */
export function useLinkDocMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ kbId, docId }: { kbId: string; docId: string }) => knowledgeApi.linkDoc(kbId, docId),
        onSuccess: (_, variables) => {
            // 刷新该知识库的文档列表
            queryClient.invalidateQueries({ queryKey: KNOWLEDGE_KEYS.DOCUMENTS(variables.kbId) });
        }
    });
}
