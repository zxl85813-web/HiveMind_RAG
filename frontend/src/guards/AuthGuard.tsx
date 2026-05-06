import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
// import { useAuthStore } from '@/stores/authStore';

interface AuthGuardProps {
    children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
    const navigate = useNavigate();
    const location = useLocation();
    // const { token, isAuthenticated } = useAuthStore();

    // 真实鉴权逻辑: 在 Mock 模式下自动放行，生产模式下校验 localStorage 中的 Token
    const isMock = import.meta.env.VITE_USE_MOCK === 'true';
    const isAuthenticated = isMock || !!localStorage.getItem('access_token');

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
