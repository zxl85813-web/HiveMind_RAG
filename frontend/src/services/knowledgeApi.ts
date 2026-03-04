/**
 * Knowledge Base API Client.
 */
import api from './api';
import type { ApiResponse, KnowledgeBase, Document, KBLink } from '../types';

export interface CreateKnowledgeBaseParams {
    name: string;
    description?: string;
    embedding_model?: string;
    is_public?: boolean;
    chunking_strategy?: string;
}

export const knowledgeApi = {
    // Knowledge Bases
    listKBs: () => api.get<ApiResponse<KnowledgeBase[]>>('/knowledge'),
    createKB: (data: CreateKnowledgeBaseParams) => api.post<ApiResponse<KnowledgeBase>>('/knowledge', data),
    getKB: (id: string) => api.get<ApiResponse<KnowledgeBase>>(`/knowledge/${id}`),

    // Global Documents
    uploadDoc: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post<Document>('/knowledge/documents', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },

    // Knowledge Base Links
    linkDoc: (kbId: string, docId: string) => api.post<KBLink>(`/knowledge/${kbId}/documents/${docId}`, {}),
    listDocsInKB: (kbId: string) => api.get<Document[]>(`/knowledge/${kbId}/documents`),
    unlinkDoc: (kbId: string, docId: string) => api.delete<{ status: string }>(`/knowledge/${kbId}/documents/${docId}`),
    getDocumentReport: (documentId: string) => api.get<ApiResponse<any>>(`/security/reports/document/${documentId}`),

    // Knowledge Graph
    getKBGraph: (kbId: string) => api.get<ApiResponse<{ nodes: any[], links: any[] }>>(`/knowledge/${kbId}/graph`),

    // Search
    searchKB: (kbId: string, query: string, search_type: string = 'hybrid', top_k: number = 5) =>
        api.post<ApiResponse<{ results: any[], context_log: string[] }>>(`/knowledge/${kbId}/search`, { query, search_type, top_k }),

    // Preview
    getDocumentPreview: (docId: string) => api.get<ApiResponse<{ text: string, job_id: string }>>(`/knowledge/documents/${docId}/preview`)
};
