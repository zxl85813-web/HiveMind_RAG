import api from './api';
import type { ApiResponse } from '../types';

export interface Subscription {
    id: string;
    topic: string;
    is_active: boolean;
    created_at: string;
}

export interface TechDiscovery {
    id: string;
    title: string;
    summary: string;
    url: string;
    category: string;
    relevance_score: number;
    discovered_at: string;
}

export const learningApi = {
    getSubscriptions: () => {
        return api.get<ApiResponse<Subscription[]>>('/learning/subscriptions');
    },
    addSubscription: (topic: string) => {
        return api.post<ApiResponse<Subscription>>('/learning/subscriptions', { topic });
    },
    deleteSubscription: (id: string) => {
        return api.delete<ApiResponse<void>>(`/learning/subscriptions/${id}`);
    },
    getDiscoveries: () => {
        return api.get<ApiResponse<TechDiscovery[]>>('/learning/discoveries');
    },
    submitFeedback: (params: { message_id: string; rating: number; comment?: string }) => {
        return api.post<ApiResponse<void>>('/learning/feedback', params);
    }
};
