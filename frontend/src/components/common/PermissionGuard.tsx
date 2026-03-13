import React from 'react';
import { Button, Tooltip } from 'antd';
import type { ButtonProps } from 'antd';
import type { AccessRequirement } from '../../config/access';
import { useAuthStore } from '../../stores/authStore';

interface PermissionGuardProps {
    access: AccessRequirement;
    mode?: 'hide' | 'disable';
    fallback?: React.ReactNode;
    children: React.ReactNode;
}

interface PermissionButtonProps extends ButtonProps {
    access: AccessRequirement;
    mode?: 'hide' | 'disable';
    denyTooltip?: string;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
    access,
    mode = 'hide',
    fallback = null,
    children,
}) => {
    const hasAccess = useAuthStore((state) => state.hasAccess);
    const allowed = hasAccess(access);

    if (allowed) {
        return <>{children}</>;
    }

    if (mode === 'hide') {
        return <>{fallback}</>;
    }

    return <>{children}</>;
};

export const PermissionButton: React.FC<PermissionButtonProps> = ({
    access,
    mode = 'hide',
    denyTooltip = '当前账号没有此操作权限',
    disabled,
    children,
    ...rest
}) => {
    const hasAccess = useAuthStore((state) => state.hasAccess);
    const allowed = hasAccess(access);

    if (!allowed && mode === 'hide') {
        return null;
    }

    const isDisabled = disabled || !allowed;
    const btn = (
        <Button {...rest} disabled={isDisabled}>
            {children}
        </Button>
    );

    if (!allowed && mode === 'disable') {
        return <Tooltip title={denyTooltip}>{btn}</Tooltip>;
    }

    return btn;
};