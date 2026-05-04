import type { AxiosResponse } from 'axios';
import api from './api';

export interface ApiResponse<T> {
    success: boolean;
    data: T;
    message: string;
}

export interface ReflectionEntry {
    id: string;
    type: string;
    agent_name: string;
    summary: string;
    details: any;
    confidence_score: number;
    action_taken: string;
    created_at: string;
}

export interface TodoItem {
    id: string;
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
    status: 'pending' | 'in_progress' | 'waiting_user' | 'completed' | 'cancelled';
    created_by: string;
    assigned_to: string;
    created_at: string;
    due_at?: string;
    completed_at?: string;
}

export interface AgentInfo {
    name: string;
    description: string;
    status: 'idle' | 'processing' | 'reflecting';
    icon: string;
    currentTask?: string;
    skills?: string[];
    tools?: string[];
    model_hint?: string | null;
    built_in?: boolean;
}

export interface SwarmStats {
    active_agents: number;
    today_requests: number;
    shared_todos: number;
    reflection_logs: number;
}

export interface McpServerStatus {
    name: string;
    status: 'connected' | 'disconnected';
    type: string;
    command: string;
    args: string[];
}

export interface McpTool {
    name: string;
    description: string;
}

export interface SkillInfo {
    name: string;
    summary?: string;
    description?: string;
    version: string;
    tags?: string[];
    tool_count?: number;
    enabled?: boolean;
    /** Legacy field used by older mocks; mapped from `enabled` when missing */
    status?: 'active' | 'inactive' | 'error';
}

export interface SkillDetail {
    name: string;
    summary?: string;
    description?: string;
    version?: string;
    tags?: string[];
    body?: string;
    tools?: { name: string; description?: string }[];
    path?: string;
    [key: string]: any;
}

export interface DAGNode {
    id: string;
    label: string;
    agent: string;
    status: 'pending' | 'running' | 'completed' | 'error' | 'warning';
}

export interface DAGLink {
    source: string;
    target: string;
}

export interface DAGData {
    nodes: DAGNode[];
    links: DAGLink[];
}

export interface TopologyNode {
    id: string;
    label: string;
    type: 'agent' | 'skill' | 'tool';
    icon?: string;
    model_hint?: string | null;
}

export interface TopologyLink {
    source: string;
    target: string;
    rel: 'uses' | 'has_tool';
}

export interface TopologyData {
    nodes: TopologyNode[];
    links: TopologyLink[];
}

export const agentApi = {
    /**
     * Get recent reflections from the swarm manager
     */
    getReflections: (limit: number = 20): Promise<AxiosResponse<ApiResponse<ReflectionEntry[]>>> => {
        return api.get<ApiResponse<ReflectionEntry[]>>(`/agents/swarm/reflections?limit=${limit}`);
    },

    /**
     * Get all registered agents
     */
    getAgents: (): Promise<AxiosResponse<ApiResponse<AgentInfo[]>>> => {
        return api.get<ApiResponse<AgentInfo[]>>('/agents/swarm/agents');
    },

    /**
     * Add or update a runtime agent (built-in agents are read-only)
     */
    upsertAgent: (payload: {
        name: string;
        description: string;
        skills?: string[];
        model_hint?: string | null;
    }): Promise<AxiosResponse<ApiResponse<{ name: string; saved: boolean }>>> => {
        return api.post('/agents/swarm/agents', payload);
    },

    /**
     * Delete a runtime agent (built-in agents cannot be deleted)
     */
    deleteAgent: (name: string): Promise<AxiosResponse<ApiResponse<{ name: string; deleted: boolean }>>> => {
        return api.delete(`/agents/swarm/agents/${encodeURIComponent(name)}`);
    },

    /**
     * Get communal TODO list
     */
    getTodos: (): Promise<AxiosResponse<ApiResponse<TodoItem[]>>> => {
        return api.get<ApiResponse<TodoItem[]>>('/agents/swarm/todos');
    },

    /**
     * Get swarm-wide statistics
     */
    getStats: (): Promise<AxiosResponse<ApiResponse<SwarmStats>>> => {
        return api.get<ApiResponse<SwarmStats>>('/agents/swarm/stats');
    },

    /**
     * Get MCP servers status
     */
    getMcpStatus: (): Promise<AxiosResponse<ApiResponse<McpServerStatus[]>>> => {
        return api.get<ApiResponse<McpServerStatus[]>>('/agents/mcp/status');
    },

    /**
     * Add or update an MCP server (persists mcp_servers.json + reconnects)
     */
    upsertMcpServer: (payload: {
        name: string;
        type?: string;
        command: string;
        args?: string[];
        env?: Record<string, string>;
    }): Promise<AxiosResponse<ApiResponse<{ name: string; saved: boolean }>>> => {
        return api.post('/agents/mcp/servers', { type: 'stdio', args: [], ...payload });
    },

    /**
     * Delete an MCP server (persists + reconnects)
     */
    deleteMcpServer: (name: string): Promise<AxiosResponse<ApiResponse<{ name: string; deleted: boolean }>>> => {
        return api.delete(`/agents/mcp/servers/${encodeURIComponent(name)}`);
    },

    /**
     * Force reconnect all MCP servers
     */
    reconnectMcp: (): Promise<AxiosResponse<ApiResponse<{ reconnected: boolean }>>> => {
        return api.post('/agents/mcp/reconnect');
    },

    /**
     * Get MCP tools available
     */
    getMcpTools: (): Promise<AxiosResponse<ApiResponse<McpTool[]>>> => {
        return api.get<ApiResponse<McpTool[]>>('/agents/mcp/tools');
    },

    /**
     * Get loaded Skills
     */
    getSkills: (): Promise<AxiosResponse<ApiResponse<SkillInfo[]>>> => {
        return api.get<ApiResponse<SkillInfo[]>>('/agents/skills');
    },

    /**
     * Get a single skill's full detail (Tier 2 - SKILL.md body + tools)
     */
    getSkillDetail: (name: string): Promise<AxiosResponse<ApiResponse<SkillDetail>>> => {
        return api.get<ApiResponse<SkillDetail>>(`/agents/skills/${encodeURIComponent(name)}`);
    },

    /**
     * Install a Skill from a ZIP archive (multipart/form-data)
     */
    installSkill: (file: File, overwrite = false): Promise<AxiosResponse<ApiResponse<{
        installed: boolean;
        name: string;
        directory: string;
        version?: string;
        tool_count?: number;
    }>>> => {
        const form = new FormData();
        form.append('file', file);
        return api.post(`/agents/skills/upload?overwrite=${overwrite}`, form, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },

    /**
     * Uninstall a Skill (and optionally delete its files on disk)
     */
    uninstallSkill: (name: string, deleteFiles = true): Promise<AxiosResponse<ApiResponse<{
        name: string; deleted: boolean; files_removed: boolean;
    }>>> => {
        return api.delete(`/agents/skills/${encodeURIComponent(name)}?delete_files=${deleteFiles}`);
    },

    /**
     * Enable/disable a Skill in-memory
     */
    toggleSkill: (name: string, enabled: boolean): Promise<AxiosResponse<ApiResponse<{
        name: string; enabled: boolean;
    }>>> => {
        return api.post(`/agents/skills/${encodeURIComponent(name)}/toggle?enabled=${enabled}`);
    },

    /**
     * Force reload of the skills directory
     */
    reloadSkills: (): Promise<AxiosResponse<ApiResponse<{
        reloaded: boolean; skill_count: number;
    }>>> => {
        return api.post('/agents/skills/reload');
    },

    /**
     * Get realtime Agent DAG Trace
     */
    getTraces: (): Promise<AxiosResponse<ApiResponse<DAGData>>> => {
        return api.get<ApiResponse<DAGData>>('/agents/swarm/traces');
    },

    /**
     * Get Agent-Skill-Tool capability topology graph
     */
    getTopology: (): Promise<AxiosResponse<ApiResponse<TopologyData>>> => {
        return api.get<ApiResponse<TopologyData>>('/agents/swarm/topology');
    }
};
