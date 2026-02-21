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

    // 模拟鉴权逻辑 (TODO: 替换为实际 Store 状态)
    const isAuthenticated = true; // 默认已登录，后续改为 token 校验

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
