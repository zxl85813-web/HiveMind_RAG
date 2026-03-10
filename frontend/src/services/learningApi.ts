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

export interface LearningSuggestion {
    title: string;
    reason: string;
    action: string;
}

export interface DailyLearningRun {
    report_date: string;
    report_path: string;
    local_materials_count: number;
    github_project_items_count: number;
    github_issues_count: number;
    external_signals_count: number;
    agent_summary: string;
    learning_tracks: string[];
    suggestions: LearningSuggestion[];
}

export interface DailyReportContent {
    report_path: string;
    content: string;
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
    runDailyCycle: () => {
        return api.post<ApiResponse<DailyLearningRun>>('/learning/daily-cycle');
    },
    getDailyReports: (limit = 7) => {
        return api.get<ApiResponse<string[]>>('/learning/daily-reports', { params: { limit } });
    },
    getDailyReportContent: (reportPath: string) => {
        return api.get<ApiResponse<DailyReportContent>>('/learning/daily-report-content', {
            params: { report_path: reportPath }
        });
    },
    submitFeedback: (params: { message_id: string; rating: number; comment?: string }) => {
        return api.post<ApiResponse<void>>('/learning/feedback', params);
    }
};
