import { create } from 'zustand';
import type { AccessRequirement } from '../config/access';
import { ROLE_PERMISSION_MAP } from '../config/access';
import { authApi } from '../services/authApi';

export type UserRole = 'admin' | 'operator' | 'viewer';

export interface UserProfile {
    id: string;
    name: string;
    roles: UserRole[];
    permissions: string[];
}

interface AuthState {
    isAuthenticated: boolean;
    isProfileLoading: boolean;
    profile: UserProfile;
    initProfile: () => Promise<void>;
    setMockRole: (role: UserRole) => void;
    setAuthenticated: (value: boolean) => void;
    hasAccess: (access?: AccessRequirement) => boolean;
}

const MOCK_ROLE_STORAGE_KEY = 'VITE_MOCK_ROLE';

function getInitialRole(): UserRole {
    const savedRole = localStorage.getItem(MOCK_ROLE_STORAGE_KEY);
    if (savedRole === 'admin' || savedRole === 'operator' || savedRole === 'viewer') {
        return savedRole;
    }
    return 'admin';
}

function buildProfileByRole(role: UserRole): UserProfile {
    return {
        id: 'mock-user-001',
        name: role === 'admin' ? 'Mock Admin' : role === 'operator' ? 'Mock Operator' : 'Mock Viewer',
        roles: [role],
        permissions: [...ROLE_PERMISSION_MAP[role]],
    };
}

function toUserRole(value?: string): UserRole {
    if (value === 'admin' || value === 'operator' || value === 'viewer') {
        return value;
    }
    return 'viewer';
}

function normalizeRemoteProfile(raw: Record<string, unknown>): UserProfile {
    const derivedRole = toUserRole(
        typeof raw.role === 'string'
            ? raw.role
            : Array.isArray(raw.roles) && typeof raw.roles[0] === 'string'
                ? raw.roles[0]
                : undefined,
    );

    const explicitPermissions = Array.isArray(raw.permissions)
        ? raw.permissions.filter((p): p is string => typeof p === 'string')
        : [];

    return {
        id: (typeof raw.id === 'string' && raw.id)
            || (typeof raw.user_id === 'string' && raw.user_id)
            || 'mock-user-001',
        name: (typeof raw.name === 'string' && raw.name)
            || (typeof raw.username === 'string' && raw.username)
            || (typeof raw.email === 'string' && raw.email)
            || 'Unknown User',
        roles: [derivedRole],
        permissions: explicitPermissions.length > 0 ? explicitPermissions : [...ROLE_PERMISSION_MAP[derivedRole]],
    };
}

const initialRole = getInitialRole();
const initialAuthenticated = true;

export const useAuthStore = create<AuthState>((set, get) => ({
    isAuthenticated: initialAuthenticated,
    isProfileLoading: false,
    profile: buildProfileByRole(initialRole),

    initProfile: async () => {
        if (import.meta.env.VITE_USE_MOCK === 'true' || import.meta.env.MODE === 'mock') {
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
            set({ isProfileLoading: false });
        }
    },

    setMockRole: (role) => {
        localStorage.setItem(MOCK_ROLE_STORAGE_KEY, role);
        set({ profile: buildProfileByRole(role) });
    },

    setAuthenticated: (value) => set({ isAuthenticated: value }),

    hasAccess: (access) => {
        if (!access) {
            return true;
        }

        const profile = get().profile;
        const roleMatched = !access.anyRoles || access.anyRoles.some((role) => profile.roles.includes(role as UserRole));
        const permissionMatched = !access.anyPermissions
            || access.anyPermissions.some((permission) => profile.permissions.includes(permission));

        return roleMatched && permissionMatched;
    },
}));