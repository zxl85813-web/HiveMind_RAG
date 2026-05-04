import axios from 'axios';

const API_BASE = '/api/v1/builder';

export interface BuilderState {
    session_id: string;
    user_id: string;
    messages: any[];
    confirmed_fields: Record<string, any>;
    missing_dimensions: string[];
    coverage_pct: number;
    discovered_context: Record<string, any>;
    research_insights: string[];
    added_features_count: number;
    scope_warning: string | null;
    golden_dataset: any[];
    generated_config: any | null;
    interview_round: number;
    next_step: string;
}

export const builderApi = {
    async sendMessage(session_id: string, user_id: string, text: string, current_state?: any) {
        return axios.post(`${API_BASE}/chat`, {
            session_id,
            user_id,
            user_input: text,
            current_state
        });
    },
    
    async getSession(session_id: string) {
        return axios.get(`${API_BASE}/sessions/${session_id}`);
    }
};
