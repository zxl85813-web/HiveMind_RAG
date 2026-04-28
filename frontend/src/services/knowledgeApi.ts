/**
 * Knowledge Base API Client.
 */
import api from './api';
import type { ApiResponse, KnowledgeBase, Document, KBLink, KnowledgeBasePermission } from '../types';

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

    // Permissions
    getPermissions: (kbId: string) => api.get<ApiResponse<KnowledgeBasePermission[]>>(`/knowledge/${kbId}/permissions`),
    addPermission: (kbId: string, data: Partial<KnowledgeBasePermission>) => api.post<ApiResponse<KnowledgeBasePermission>>(`/knowledge/${kbId}/permissions`, data),
    deletePermission: (kbId: string, permId: string) => api.delete<ApiResponse<{ status: string }>>(`/knowledge/${kbId}/permissions/${permId}`),

    // Global Documents
    uploadDoc: (file: File, folderPath?: string) => {
        const formData = new FormData();
        formData.append('file', file);
        if (folderPath) formData.append('folder_path', folderPath);
        return api.post<Document>('/knowledge/documents', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },

    /** 批量上传（每批最多 20 个文件），返回 batch_id 和各文件结果 */
    uploadDocsBatch: (
        files: File[],
        folderPaths: (string | undefined)[],
        onUploadProgress?: (percent: number) => void,
    ) => {
        const formData = new FormData();
        files.forEach((f, i) => {
            formData.append('files', f);
            if (folderPaths[i]) {
                formData.append(`folder_paths[${i}]`, folderPaths[i]!);
            }
        });
        return api.post<{
            total: number;
            succeeded: number;
            failed: number;
            documents: Array<{
                doc_id?: string;
                filename: string;
                folder_path?: string;
                status: 'pending' | 'failed';
                error?: string;
            }>;
        }>('/knowledge/documents/batch', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: onUploadProgress
                ? (e) => {
                    const pct = e.total ? Math.round((e.loaded / e.total) * 100) : 0;
                    onUploadProgress(pct);
                }
                : undefined,
        });
    },

    /** 批量关联到 KB，返回 batch_id 供 SSE 订阅 */
    linkDocsBatch: (kbId: string, docIds: string[]) =>
        api.post<{ batch_id: string; linked: number }>(`/knowledge/${kbId}/documents/batch`, { doc_ids: docIds }),

    /** 获取批次进度快照（轮询备用） */
    getBatchProgress: (batchId: string) =>
        api.get<{ total: number; completed: number; failed: number; percent: number; status: string }>(
            `/knowledge/batches/${batchId}/progress/snapshot`
        ),

    // Knowledge Base Links
    linkDoc: (kbId: string, docId: string) => api.post<KBLink>(`/knowledge/${kbId}/documents/${docId}`, {}),
    listDocsInKB: (kbId: string) => api.get<Document[]>(`/knowledge/${kbId}/documents`),
    unlinkDoc: (kbId: string, docId: string) => api.delete<{ status: string }>(`/knowledge/${kbId}/documents/${docId}`),
    getDocumentReport: (documentId: string) => api.get<ApiResponse<Record<string, unknown>>>(`/security/reports/document/${documentId}`),

    // Knowledge Graph
    getKBGraph: (kbId: string) => api.get<ApiResponse<{ nodes: Record<string, unknown>[], links: Record<string, unknown>[] }>>(`/knowledge/${kbId}/graph`),

    // Search
    searchKB: (kbId: string, query: string, search_type: string = 'hybrid', top_k: number = 5) =>
        api.post<ApiResponse<{ results: unknown[], context_log: string[] }>>(`/knowledge/${kbId}/search`, { query, search_type, top_k }),

    // Preview
    getDocumentPreview: (docId: string) => api.get<ApiResponse<{ text: string, job_id: string }>>(`/knowledge/documents/${docId}/preview`)
};
