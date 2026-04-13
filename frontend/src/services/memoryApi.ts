import api from './api';
import { ApiResponse } from '../types';

export interface GraphNode {
    id: string;
    name: string;
    label: string;
    color?: string;
    val?: number;
}

export interface GraphLink {
    source: string;
    target: string;
    type: string;
}

export interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

export interface EpisodicMemory {
    id: string;
    user_id: string;
    conversation_id: string;
    agent_names: string[];
    summary: string;
    key_decisions: string[];
    topics: string[];
    user_intent: string;
    message_count: number;
    topic_coverage: number;
    temperature: number;
    recall_count: number;
    created_at: string;
}

export const memoryApi = {
    /**
     * Get graph neighborhood for entities.
     */
    getGraph: (entities: string[]) => {
        const params = new URLSearchParams();
        entities.forEach(e => params.append('entities', e));
        return api.get<GraphData>(`/memory/graph?${params.toString()}`);
    },

    /**
     * List episodic memories (EP-010).
     */
    listEpisodes: (limit = 20, offset = 0) => 
        api.get<ApiResponse<EpisodicMemory[]>>(`/memory/episodes?limit=${limit}&offset=${offset}`),

    /**
     * Get single episodic memory detail.
     */
    getEpisode: (id: string) => 
        api.get<ApiResponse<EpisodicMemory>>(`/memory/episodes/${id}`),

    /**
     * Delete an episodic memory.
     */
    deleteEpisode: (id: string) => 
        api.delete<ApiResponse<any>>(`/memory/episodes/${id}`)
};
