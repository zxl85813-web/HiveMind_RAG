import type { AxiosResponse } from 'axios';
import api from './api';

import type { ApiResponse } from '../types';

export interface ReflectionEntry {
    id: string;
    type: string;
    agent_name: string;
    summary: string;
    details: Record<string, unknown>;
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
    description: string;
    version: string;
    status: 'active' | 'error';
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
     * Get realtime Agent DAG Trace
     */
    getTraces: (): Promise<AxiosResponse<ApiResponse<DAGData>>> => {
        return api.get<ApiResponse<DAGData>>('/agents/swarm/traces');
    }
};
