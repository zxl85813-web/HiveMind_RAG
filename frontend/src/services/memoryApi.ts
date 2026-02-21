import api from './api';

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

export const memoryApi = {
    /**
     * Get graph neighborhood for entities.
     */
    getGraph: (entities: string[]) => {
        const params = new URLSearchParams();
        entities.forEach(e => params.append('entities', e));
        return api.get<GraphData>(`/memory/graph?${params.toString()}`);
    }
};
