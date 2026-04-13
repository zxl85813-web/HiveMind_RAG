import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { AccessRequirement } from '../config/access';
import { useAuthStore } from '../stores/authStore';

interface AccessGuardProps {
    children: React.ReactNode;
    access?: AccessRequirement;
}

export const AccessGuard: React.FC<AccessGuardProps> = ({ children, access }) => {
    const location = useLocation();
    const hasAccess = useAuthStore((state) => state.hasAccess);
    const profile = useAuthStore((state) => state.profile);
    const isInitialized = useAuthStore((state) => state.isInitialized);
    const isProfileLoading = useAuthStore((state) => state.isProfileLoading);

    // 🛰️ [Auth-Gate]: 只有当 Profile 准确同步完成后，才执行权限判断。
    // 防止在刷新页面的瞬间，由于初始状态为 'user' 导致被 AccessGuard 错误拦截。
    if (!isInitialized || isProfileLoading) {
        return null; // 或者返回 <LoadingState />
    }

    if (!hasAccess(access)) {
        console.warn('[AccessGuard] Access Denied:', { access, currentProfile: profile });
        return <Navigate to="/forbidden" replace state={{ from: location.pathname }} />;
    }

    return <>{children}</>;
};