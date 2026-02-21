import api from './api';

export interface GenerateRequest {
    task_description: string;
    kb_ids: string[];
}

export interface GenerateResponse {
    status: string;
    message: string;
    artifact_path?: string;
    step_logs: string[];
    draft?: {
        headers: string[];
        rows: any[];
    }
}

export const generationApi = {
    run: async (payload: GenerateRequest): Promise<GenerateResponse> => {
        const response = await api.post('/generation/run', payload);
        return response.data;
    }
};
