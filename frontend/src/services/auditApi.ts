import api from './api';
import type { ApiResponse, DocumentReview } from '../types';

export const auditApi = {
    getQueue: () =>
        api.get<ApiResponse<DocumentReview[]>>('/audit/queue'),

    getDocumentReviews: (documentId: string) =>
        api.get<ApiResponse<DocumentReview[]>>(`/audit/document/${documentId}`),

    approve: (reviewId: string, comment?: string) =>
        api.post<ApiResponse<DocumentReview>>(`/audit/${reviewId}/approve`, null, { params: { comment } }),

    reject: (reviewId: string, comment?: string) =>
        api.post<ApiResponse<DocumentReview>>(`/audit/${reviewId}/reject`, null, { params: { comment } }),

    updateReview: (reviewId: string, data: { status: string, reviewer_comment: string }) =>
        api.put<ApiResponse<DocumentReview>>(`/audit/${reviewId}`, data)
};

export default auditApi;
