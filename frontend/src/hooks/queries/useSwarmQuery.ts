import { useQuery } from '@tanstack/react-query';
import { agentApi } from '../../services/agentApi';

/**
 * 🛰️ [FE-GOV-001]: Swarm / Agent 集群状态管理 Hook
 */

export const SWARM_KEYS = {
    REFLECTIONS: ['swarm', 'reflections'] as const,
    AGENTS: ['swarm', 'agents'] as const,
    STATS: ['swarm', 'stats'] as const,
    TODOS: ['swarm', 'todos'] as const,
    TRACES: ['swarm', 'traces'] as const,
};

const SWARM_REFRESH_INTERVAL = 10000; // 10s 自动刷新

/** 获取自省日志 */
export function useSwarmReflections(limit = 20) {
    return useQuery({
        queryKey: [...SWARM_KEYS.REFLECTIONS, limit],
        queryFn: async () => {
            const res = await agentApi.getReflections(limit);
            return res.data.data || [];
        },
        refetchInterval: SWARM_REFRESH_INTERVAL,
    });
}

/** 获取 Agent 列表 */
export function useSwarmAgents() {
    return useQuery({
        queryKey: SWARM_KEYS.AGENTS,
        queryFn: async () => {
            const res = await agentApi.getAgents();
            return res.data.data || [];
        },
        refetchInterval: SWARM_REFRESH_INTERVAL,
    });
}

/** 获取集群统计指标 */
export function useSwarmStats() {
    return useQuery({
        queryKey: SWARM_KEYS.STATS,
        queryFn: async () => {
            const res = await agentApi.getStats();
            return res.data.data || { 
                active_agents: 0, 
                today_requests: 0, 
                shared_todos: 0, 
                reflection_logs: 0 
            };
        },
        refetchInterval: SWARM_REFRESH_INTERVAL,
    });
}

/** 获取协同任务队列 */
export function useSwarmTodos() {
    return useQuery({
        queryKey: SWARM_KEYS.TODOS,
        queryFn: async () => {
            const res = await agentApi.getTodos();
            return res.data.data || [];
        },
        refetchInterval: SWARM_REFRESH_INTERVAL,
    });
}

/** 获取实时链路追踪 (DAG) */
export function useSwarmTraces() {
    return useQuery({
        queryKey: SWARM_KEYS.TRACES,
        queryFn: async () => {
            const res = await agentApi.getTraces();
            return res.data.data || { nodes: [], links: [] };
        },
        refetchInterval: 5000, // Trace 刷新率更高: 5s
    });
}
