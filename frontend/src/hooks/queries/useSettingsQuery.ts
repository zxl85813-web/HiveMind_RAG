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
            return res.data;
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
