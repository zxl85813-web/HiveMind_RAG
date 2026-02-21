import api from './api';

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

export const agentApi = {
    /**
     * Get recent reflections from the swarm manager
     */
    getReflections: (limit: number = 20) => {
        return api.get<ReflectionEntry[]>(`/agents/swarm/reflections?limit=${limit}`);
    },

    /**
     * Get all registered agents
     */
    getAgents: () => {
        return api.get<AgentInfo[]>('/agents/swarm/agents');
    },

    /**
     * Get swarm-wide statistics
     */
    getStats: () => {
        return api.get<SwarmStats>('/agents/swarm/stats');
    }
};
