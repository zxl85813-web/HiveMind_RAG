import { create } from 'zustand';
import type { AccessRequirement } from '../config/access';
import { ROLE_PERMISSION_MAP } from '../config/access';
import { authApi } from '../services/authApi';
import { tokenVault } from '../core/auth/TokenVault';
import { connectionManager } from '../core/ConnectionManager';

export type UserRole = 'admin' | 'user' | 'readonly';

export interface UserProfile {
    id: string;
    name: string;
    roles: UserRole[];
    permissions: string[];
}

interface AuthState {
    isAuthenticated: boolean;
    isProfileLoading: boolean;
    isInitialized: boolean;
    profile: UserProfile;
    initProfile: () => Promise<void>;
    setMockRole: (role: UserRole) => void;
    setAuthenticated: (value: boolean, user?: any) => void;
    hasAccess: (access?: AccessRequirement) => boolean;
}

const MOCK_ROLE_STORAGE_KEY = 'VITE_MOCK_ROLE';

function getInitialRole(): UserRole {
    const savedRole = localStorage.getItem(MOCK_ROLE_STORAGE_KEY);
    if (savedRole === 'admin' || savedRole === 'user' || savedRole === 'readonly') {
        return savedRole;
    }
    return 'user';
}

function buildProfileByRole(role: UserRole): UserProfile {
    return {
        id: 'mock-user-001',
        name: role === 'admin' ? 'Mock Admin' : role === 'user' ? 'Mock User' : 'Mock Viewer',
        roles: [role],
        permissions: [...(ROLE_PERMISSION_MAP[role] || [])],
    };
}

function toUserRole(value?: string): UserRole {
    if (!value) return 'readonly';
    const normalized = value.toLowerCase().trim();
    if (normalized === 'admin' || normalized === 'user' || normalized === 'readonly') {
        return normalized as UserRole;
    }
    return 'readonly';
}

function normalizeRemoteProfile(raw: Record<string, unknown>): UserProfile {
    // 🛡️ [Harden]: Support nested data structure often returned by ApiResponse wrapper
    const data = (raw && typeof raw === 'object' && 'data' in raw)
        ? (raw as { data: Record<string, unknown> }).data
        : raw;

    const derivedRole = toUserRole(
        typeof data.role === 'string'
            ? data.role
            : Array.isArray(data.roles) && typeof data.roles[0] === 'string'
                ? data.roles[0]
                : undefined,
    );

    const explicitPermissions = Array.isArray(data.permissions)
        ? data.permissions.filter((p): p is string => typeof p === 'string')
        : [];

    return {
        id: (typeof data.id === 'string' && data.id)
            || (typeof data.user_id === 'string' && data.user_id)
            || 'mock-user-001',
        name: (typeof data.name === 'string' && data.name)
            || (typeof data.username === 'string' && data.username)
            || (typeof data.email === 'string' && data.email)
            || 'Unknown User',
        roles: [derivedRole],
        permissions: explicitPermissions.length > 0 ? explicitPermissions : [...ROLE_PERMISSION_MAP[derivedRole]],
    };
}

const initialRole = getInitialRole();
const initialAuthenticated = !!tokenVault.getAccessToken();

export const useAuthStore = create<AuthState>((set, get) => ({
    isAuthenticated: initialAuthenticated,
    isProfileLoading: false,
    isInitialized: false,
    profile: buildProfileByRole(initialRole),

    initProfile: async () => {
        if (import.meta.env.VITE_USE_MOCK === 'true' || import.meta.env.MODE === 'mock') {
            return;
        }

        // 🛡️ [Auth-Optimization]: 如果本地没有 Token，直接跳过请求，防止后端返回 401 触发拦截器重定向死循环
        if (!tokenVault.getAccessToken()) {
            set({ isProfileLoading: false });
            return;
        }

        set({ isProfileLoading: true });
        try {
            const res = await authApi.getCurrentUser();
            const payload = res.data;
            const data = (payload && typeof payload === 'object' && 'data' in payload)
                ? (payload as { data: unknown }).data
                : payload;

            if (data && typeof data === 'object') {
                set({ profile: normalizeRemoteProfile(data as Record<string, unknown>) });
            }
        } catch {
            // Keep local role-based profile if profile endpoint is not available yet.
        } finally {
            set({ isProfileLoading: false, isInitialized: true });
        }
    },

    setMockRole: (role) => {
        localStorage.setItem(MOCK_ROLE_STORAGE_KEY, role);
        set({ profile: buildProfileByRole(role) });
    },

    setAuthenticated: (value, user) => {
        if (!value) {
            tokenVault.clear();
            connectionManager.abortAll();
            set({ isAuthenticated: false, profile: buildProfileByRole('readonly') });
        } else {
            // 🛰️ [FE-GOV-FIX]: 登录成功后，如果登录接口返回了 User 信息，立即更新 Profile
            // 避免在跳转到 Dashboard 时出现权限判断滞后（导致菜单闪烁或缺失）。
            if (user) {
                set({ 
                    isAuthenticated: true, 
                    isInitialized: true,
                    profile: normalizeRemoteProfile(user) 
                });
            } else {
                set({ isAuthenticated: true });
            }
            // 无论如何，尝试从后端拉取最权威的 Profile 状态
            get().initProfile();
        }
    },

    hasAccess: (access) => {
        const { profile } = get();
        
        // 🚀 [Hardening]: Admin bypassing permission checks (Case-Insensitive)
        if (profile?.roles?.some(r => r.toLowerCase() === 'admin')) {
            return true;
        }

        if (!access) {
            return true;
        }

        const roleMatched = !access.anyRoles || access.anyRoles.some((role) => profile.roles.includes(role as UserRole));
        const permissionMatched = !access.anyPermissions
            || access.anyPermissions.some((permission) => profile.permissions.includes(permission));

        return roleMatched && permissionMatched;
    },
}));