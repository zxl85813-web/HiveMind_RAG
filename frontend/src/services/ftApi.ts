import api from './api';
import type { ApiResponse, FineTuningItem } from '../types';

export const ftApi = {
    createItem: (data: Partial<FineTuningItem>) =>
        api.post<ApiResponse<FineTuningItem>>('/finetuning/items', data),

    getItems: () =>
        api.get<ApiResponse<FineTuningItem[]>>('/finetuning/items'),

    deleteItem: (itemId: string) =>
        api.delete<ApiResponse<null>>(`/finetuning/items/${itemId}`),
};

export default ftApi;
