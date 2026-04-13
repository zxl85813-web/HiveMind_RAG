import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentApi } from '../../services/agentApi';
import { settingsApi, type PlatformKnowledge } from '../../services/settingsApi';

/**
 * 🛰️ [FE-GOV-001]: 系统设置与 MCP 状态管理 Hook
 */

export const SETTINGS_KEYS = {
    MCP_STATUS: ['settings', 'mcp-status'] as const,
    MCP_TOOLS: ['settings', 'mcp-tools'] as const,
    SKILLS: ['settings', 'skills'] as const,
    PLATFORM_KB: ['settings', 'platform-kb'] as const,
};

// --- MCP & Skills ---

/** 获取 MCP 服务器状态 */
export function useMcpStatus() {
    return useQuery({
        queryKey: SETTINGS_KEYS.MCP_STATUS,
        queryFn: async () => {
            const res = await agentApi.getMcpStatus();
            return res.data.data || [];
        },
    });
}

/** 获取 MCP 工具列表 */
export function useMcpTools() {
    return useQuery({
        queryKey: SETTINGS_KEYS.MCP_TOOLS,
        queryFn: async () => {
            const res = await agentApi.getMcpTools();
            return res.data.data || [];
        },
    });
}

/** 获取技能注册中心 */
export function useSkills() {
    return useQuery({
        queryKey: SETTINGS_KEYS.SKILLS,
        queryFn: async () => {
            const res = await agentApi.getSkills();
            return res.data.data || [];
        },
    });
}

// --- Platform Knowledge (AI Context) ---

/** 获取平台内置知识库 */
export function usePlatformKnowledge() {
    return useQuery({
        queryKey: SETTINGS_KEYS.PLATFORM_KB,
        queryFn: async () => {
            const res = await settingsApi.getPlatformKnowledge();
            return res.data.data;
        },
    });
}

/** 更新平台内置知识库 Mutation */
export function useUpdatePlatformKnowledgeMutation() {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: (data: PlatformKnowledge) => settingsApi.updatePlatformKnowledge(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: SETTINGS_KEYS.PLATFORM_KB });
        }
    });
}

// --- LLM Governance (L5) ---


export const LLM_GOV_KEYS = {
    CONFIG: ['settings', 'llm-governance'] as const,
    TASKS: ['settings', 'governance-tasks'] as const,
    INSIGHTS: ['settings', 'governance-insights'] as const,
};

/** 获取 LLM 治理配置 */
export function useLlmGovernance() {
    return useQuery({
        queryKey: LLM_GOV_KEYS.CONFIG,
        queryFn: async () => {
            const res = await settingsApi.getLlmGovernance();
            return res.data.data;
        },
    });
}

/** 获取智体提报任务 (L5) */
export function useGovernanceTasks() {
    return useQuery({
        queryKey: LLM_GOV_KEYS.TASKS,
        queryFn: async () => {
            const res = await settingsApi.getGovernanceTasks();
            return res.data.data || [];
        },
    });
}

/** 获取自适应治理建议 (Insights) */
export function useAdaptiveInsights() {
    return useQuery({
        queryKey: LLM_GOV_KEYS.INSIGHTS,
        queryFn: async () => {
            const res = await settingsApi.getAdaptiveInsights();
            return res.data.data || [];
        },
    });
}

/** 更新 LLM 治理配置 Mutation */
export function useUpdateLlmGovernanceMutation() {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: (data: any) => settingsApi.updateLlmGovernance(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: LLM_GOV_KEYS.CONFIG });
        }
    });
}
