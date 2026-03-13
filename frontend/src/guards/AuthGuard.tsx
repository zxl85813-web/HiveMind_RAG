import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

interface AuthGuardProps {
    children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

    useEffect(() => {
        if (!isAuthenticated) {
            navigate('/login', {
                replace: true,
                state: { from: location.pathname } // 登录后跳回原页面
            });
        }
    }, [isAuthenticated, navigate, location]);

    // 如果未登录，返回 null (避免渲染受保护内容)
    if (!isAuthenticated) {
        return null;
    }

    return <>{children}</>;
};
