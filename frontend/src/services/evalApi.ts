import api from './api';
import type { ApiResponse, EvaluationSet, EvaluationReport } from '../types';

export const evalApi = {
    createTestset: (kbId: string, name: string, count: number = 10) =>
        api.post<ApiResponse<string>>('/evaluation/testset', { kb_id: kbId, name, count }),

    getTestsets: () =>
        api.get<ApiResponse<EvaluationSet[]>>('/evaluation/testsets'),

    runEvaluation: (setId: string, modelName?: string, applyReflection: boolean = false) =>
        api.post<ApiResponse<string>>(`/evaluation/${setId}/evaluate`, { model_name: modelName, apply_reflection: applyReflection }),

    getReports: () =>
        api.get<ApiResponse<EvaluationReport[]>>('/evaluation/reports'),

    getReport: (reportId: string) =>
        api.get<ApiResponse<EvaluationReport>>(`/evaluation/reports/${reportId}`),

    getBadCases: () =>
        api.get<ApiResponse<unknown[]>>('/evaluation/badcases'),

    updateBadCase: (caseId: string, status: string, expectedAnswer?: string, reason?: string) =>
        api.put<ApiResponse<Record<string, unknown>>>(`/evaluation/badcases/${caseId}`, { status, expected_answer: expectedAnswer, reason }),

    deleteBadCase: (caseId: string) =>
        api.delete<ApiResponse<string>>(`/evaluation/badcases/${caseId}`),

    getKBStats: (kbId: string) =>
        api.get<ApiResponse<Record<string, unknown>>>(`/evaluation/stats/kb/${kbId}`),

    promoteBadCase: (caseId: string) =>
        api.post<ApiResponse<Record<string, any>>>(`/evaluation/badcases/${caseId}/promote`),

    getDirectives: () =>
        api.get<ApiResponse<any[]>>('/evaluation/directives'),

    assistClaims: (answer: string) =>
        api.post<ApiResponse<string[]>>('/evaluation/sme/assist-claims', { answer }),

    verifySMEAnswer: (answer: string, context: string) =>
        api.post<ApiResponse<{ is_consistent: boolean, issues: string[] }>>('/evaluation/sme/verify-consistency', { answer, context }),

    submitSMEGoldCase: (question: string, answer: string, context?: string) =>
        api.post<ApiResponse<string>>('/evaluation/sme/submit', { question, answer, context })
};

export default evalApi;
