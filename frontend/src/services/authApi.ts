import api from './api';
import type { ApiResponse } from '../types';

export interface CurrentUserResponse {
    id?: string;
    user_id?: string;
    name?: string;
    username?: string;
    email?: string;
    role?: string;
    roles?: string[];
    permissions?: string[];
}

const profileEndpoint = import.meta.env.VITE_AUTH_PROFILE_ENDPOINT || '/auth/me';

export const authApi = {
    getCurrentUser: () => api.get<ApiResponse<CurrentUserResponse> | CurrentUserResponse>(profileEndpoint),
};