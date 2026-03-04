import api from './api';
import type { ApiResponse, EvaluationSet, EvaluationReport } from '../types';

export const evalApi = {
    createTestset: (kbId: string, name: string, count: number = 10) =>
        api.post<ApiResponse<string>>('/evaluation/testset', { kb_id: kbId, name, count }),

    getTestsets: () =>
        api.get<ApiResponse<EvaluationSet[]>>('/evaluation/testsets'),

    runEvaluation: (setId: string, modelName?: string) =>
        api.post<ApiResponse<string>>(`/evaluation/${setId}/evaluate`, { model_name: modelName }),

    getReports: () =>
        api.get<ApiResponse<EvaluationReport[]>>('/evaluation/reports'),

    getReport: (reportId: string) =>
        api.get<ApiResponse<EvaluationReport>>(`/evaluation/reports/${reportId}`),

    getBadCases: () =>
        api.get<ApiResponse<any[]>>('/evaluation/badcases'),

    updateBadCase: (caseId: string, status: string, expectedAnswer?: string, reason?: string) =>
        api.put<ApiResponse<any>>(`/evaluation/badcases/${caseId}`, { status, expected_answer: expectedAnswer, reason }),

    deleteBadCase: (caseId: string) =>
        api.delete<ApiResponse<string>>(`/evaluation/badcases/${caseId}`),

    getKBStats: (kbId: string) =>
        api.get<ApiResponse<any>>(`/evaluation/stats/kb/${kbId}`)
};

export default evalApi;
