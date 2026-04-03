import { useQuery } from '@tanstack/react-query';
import { agentApi } from '../../services/agentApi';
import { knowledgeApi } from '../../services/knowledgeApi';
import { evalApi } from '../../services/evalApi';
import { observabilityApi } from '../../services/observabilityApi';
import { useMonitor } from '../useMonitor';

/**
 * 🛰️ [FE-GOV-001]: Dashboard 概览数据管理 Hook
 */

export const DASHBOARD_KEYS = {
    STATS: ['dashboard', 'stats'] as const,
    REPORTS: ['dashboard', 'reports'] as const,
    LLM_METRICS: ['dashboard', 'llm-metrics'] as const,
};

/** 聚合仪表盘统计数据 */
export function useDashboardStats() {
    const { track } = useMonitor();

    return useQuery({
        queryKey: DASHBOARD_KEYS.STATS,
        queryFn: async () => {
            track('system', 'fetch_start', { resource: 'dashboard_stats' });
            const [statsRes, kbRes] = await Promise.all([
                agentApi.getStats(),
                knowledgeApi.listKBs()
            ]);
            
            const data = {
                ...statsRes.data.data,
                total_kbs: kbRes.data.data.length
            };
            track('system', 'fetch_success', { resource: 'dashboard_stats' });
            return data;
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

/** [M7.1] 获取 LLM 模型性能与 Token 监控数据 */
export function useLLMMetrics(days = 1) {
    return useQuery({
        queryKey: [...DASHBOARD_KEYS.LLM_METRICS, days],
        queryFn: async () => {
            const res = await observabilityApi.getLLMMetrics(days);
            return res.data.data;
        },
        staleTime: 1000 * 30, // 30秒更新一次
        refetchInterval: 1000 * 60, // 1分钟自动轮询
    });
}

/** [M5.2.3] 获取 RAG 全链路追踪数据 */
export function useTraces(kbId?: string, limit = 50) {
    return useQuery({
        queryKey: ['dashboard', 'traces', kbId, limit],
        queryFn: async () => {
            const res = await observabilityApi.getTraces({ kb_id: kbId, limit });
            return (res as any).data;
        },
        staleTime: 1000 * 10, // 10秒
    });
}

/** [M5.2.4] 获取知识库使用分析看板数据 */
export function useKBAnalytics(kbId?: string, days = 7) {
    return useQuery({
        queryKey: ['dashboard', 'kb-analytics', kbId, days],
        queryFn: async () => {
            const [quality, hot, cold] = await Promise.all([
                observabilityApi.getRetrievalQuality({ kb_id: kbId, days }),
                observabilityApi.getHotQueries({ kb_id: kbId, days }),
                kbId ? observabilityApi.getColdDocuments(kbId, { days }) : Promise.resolve({ data: { data: [] } })
            ]);

            return {
                quality: quality.data.data,
                hotQueries: hot.data.data,
                coldDocuments: cold.data.data
            };
        },
        staleTime: 1000 * 60 * 5, // 5分钟
    });
}
