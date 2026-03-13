import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { SecurityPage } from './SecurityPage';
import { useAuthStore } from '../stores/authStore';
import { securityApi } from '../services/securityApi';

// Controls whether PermissionButton renders its children
let allowButtonAccess = false;

vi.mock('antd', async () => {
    const actual = await vi.importActual('antd');
    return {
        ...actual,
        App: {
            useApp: () => ({
                message: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
            }),
        },
    };
});

vi.mock('react-i18next', () => ({
    useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock('../stores/authStore', () => ({
    useAuthStore: vi.fn(),
}));

vi.mock('../services/securityApi', () => ({
    securityApi: {
        listPolicies: vi.fn(),
        getDetectors: vi.fn(),
        listAuditLogs: vi.fn(),
        activatePolicy: vi.fn(),
        createPolicy: vi.fn(),
        getDocumentPermissions: vi.fn(),
        revokePermission: vi.fn(),
        grantPermission: vi.fn(),
    },
}));

vi.mock('../components/common', () => ({
    PageContainer: ({ actions, children }: any) => (
        <div>
            <div data-testid="page-actions">{actions}</div>
            <div data-testid="page-content">{children}</div>
        </div>
    ),
    PermissionButton: ({ children, ...rest }: any) => {
        if (!allowButtonAccess) return null;
        return <button {...rest}>{children}</button>;
    },
}));

describe('SecurityPage Permission', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(securityApi.listPolicies).mockResolvedValue({ data: { data: [] } } as any);
        vi.mocked(securityApi.getDetectors).mockResolvedValue({
            data: { data: { available_detectors: [] } },
        } as any);
        vi.mocked(securityApi.listAuditLogs).mockResolvedValue({ data: { data: [] } } as any);
    });

    it('hides 新建脱敏策略 button without security:manage permission', async () => {
        allowButtonAccess = false;
        vi.mocked(useAuthStore).mockImplementation((selector: any) =>
            selector({ hasAccess: () => false }),
        );

        render(
            <MemoryRouter>
                <SecurityPage />
            </MemoryRouter>,
        );

        await waitFor(() => {
            expect(securityApi.listPolicies).toHaveBeenCalledTimes(1);
        });

        expect(screen.queryByRole('button', { name: '新建脱敏策略' })).not.toBeInTheDocument();
    });

    it('shows 新建脱敏策略 button with security:manage permission', async () => {
        allowButtonAccess = true;
        vi.mocked(useAuthStore).mockImplementation((selector: any) =>
            selector({ hasAccess: () => true }),
        );

        render(
            <MemoryRouter>
                <SecurityPage />
            </MemoryRouter>,
        );

        await waitFor(() => {
            expect(securityApi.listPolicies).toHaveBeenCalledTimes(1);
        });

        expect(screen.getByRole('button', { name: '新建脱敏策略' })).toBeInTheDocument();
    });
});
