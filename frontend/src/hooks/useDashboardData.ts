import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentApi } from '../services/agentApi';
import { knowledgeApi, type CreateKnowledgeBaseParams } from '../services/knowledgeApi';
import { evalApi } from '../services/evalApi';

/**
 * 🛰️ [Architecture-Gate]: 仪表盘数据 Hook 集
 */

export const useDashboardStats = () => {
    return useQuery({
        queryKey: ['dashboard', 'stats'],
        queryFn: async () => {
            const [statsRes, kbRes] = await Promise.all([
                agentApi.getStats(),
                knowledgeApi.listKBs()
            ]);
            return {
                active_agents: statsRes.data.data.active_agents,
                today_requests: statsRes.data.data.today_requests,
                reflection_logs: statsRes.data.data.reflection_logs,
                total_kbs: kbRes.data.data.length
            };
        }
    });
};

export const useRecentReports = () => {
    return useQuery({
        queryKey: ['dashboard', 'reports'],
        queryFn: async () => {
            const res = await evalApi.getReports();
            return res.data.data.slice(0, 3);
        }
    });
};

/**
 * 🛰️ [Architecture-Gate]: 知识库操作 Hook 集
 */

export const useCreateKnowledgeBase = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (params: CreateKnowledgeBaseParams) => knowledgeApi.createKB(params),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['knowledge', 'list'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] });
        }
    });
};

export const useKnowledgeBases = () => {
    return useQuery({
        queryKey: ['knowledge', 'list'],
        queryFn: async () => {
            const res = await knowledgeApi.listKBs();
            return res.data.data;
        }
    });
};
