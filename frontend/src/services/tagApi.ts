import api from './api';
import type { ApiResponse, Tag, TagCategory } from '../types';

export interface CreateCategoryParams {
    name: string;
    description?: string;
    color?: string;
    is_system?: boolean;
}

export interface CreateTagParams {
    name: string;
    category_id?: number | null;
    color?: string;
}

export const tagApi = {
    // Categories
    listCategories: () => api.get<ApiResponse<TagCategory[]>>('/tags/categories'),
    createCategory: (data: CreateCategoryParams) => api.post<ApiResponse<TagCategory>>('/tags/categories', data),

    // Tags
    listTags: (categoryId?: number) => api.get<ApiResponse<Tag[]>>('/tags', { params: { category_id: categoryId } }),
    createTag: (data: CreateTagParams) => api.post<ApiResponse<Tag>>('/tags', data),
    deleteTag: (tagId: number) => api.delete<ApiResponse>(`/tags/${tagId}`),

    // Document Tags
    attachTag: (documentId: string, tagId: number) => api.post<ApiResponse>(`/tags/documents/${documentId}/attach`, { tag_id: tagId }),
    detachTag: (documentId: string, tagId: number) => api.delete<ApiResponse>(`/tags/documents/${documentId}/tags/${tagId}`)
};
