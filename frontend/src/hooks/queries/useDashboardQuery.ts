import { useQuery } from '@tanstack/react-query';
import { agentApi } from '../../services/agentApi';
import { knowledgeApi } from '../../services/knowledgeApi';
import { evalApi } from '../../services/evalApi';

/**
 * 🛰️ [FE-GOV-001]: Dashboard 概览数据管理 Hook
 */

export const DASHBOARD_KEYS = {
    STATS: ['dashboard', 'stats'] as const,
    REPORTS: ['dashboard', 'reports'] as const,
};

/** 聚合仪表盘统计数据 */
export function useDashboardStats() {
    return useQuery({
        queryKey: DASHBOARD_KEYS.STATS,
        queryFn: async () => {
            const [statsRes, kbRes] = await Promise.all([
                agentApi.getStats(),
                knowledgeApi.listKBs()
            ]);
            
            return {
                ...statsRes.data.data,
                total_kbs: kbRes.data.data.length
            };
        },
        staleTime: 1000 * 60 * 2, // 2分钟缓存
    });
}

/** 获取近期质量评估报告 */
export function useRecentReports(limit = 3) {
    return useQuery({
        queryKey: DASHBOARD_KEYS.REPORTS,
        queryFn: async () => {
            const res = await evalApi.getReports();
            return res.data.data.slice(0, limit);
        },
        staleTime: 1000 * 60 * 5,
    });
}
