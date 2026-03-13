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

    if (!hasAccess(access)) {
        return <Navigate to="/forbidden" replace state={{ from: location.pathname }} />;
    }

    return <>{children}</>;
};