import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { EvalPage } from './EvalPage';
import { useAuthStore } from '../stores/authStore';
import { evalApi } from '../services/evalApi';
import { knowledgeApi } from '../services/knowledgeApi';

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

vi.mock('../stores/authStore', () => ({
    useAuthStore: vi.fn(),
}));

vi.mock('../services/evalApi', () => ({
    evalApi: {
        getTestsets: vi.fn(),
        getReports: vi.fn(),
        getBadCases: vi.fn(),
        createTestset: vi.fn(),
        runEvaluation: vi.fn(),
    },
}));

vi.mock('../services/knowledgeApi', () => ({
    knowledgeApi: {
        listKBs: vi.fn(),
    },
}));

vi.mock('../components/common/PageContainer', () => ({
    PageContainer: ({ actions, children }: any) => (
        <div>
            <div data-testid="page-actions">{actions}</div>
            <div data-testid="page-content">{children}</div>
        </div>
    ),
}));

vi.mock('../components/common', () => ({
    PermissionButton: ({ children, ...rest }: any) => {
        if (!allowButtonAccess) return null;
        return <button {...rest}>{children}</button>;
    },
}));

describe('EvalPage Permission', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(evalApi.getTestsets).mockResolvedValue({ data: { data: [] } } as any);
        vi.mocked(evalApi.getReports).mockResolvedValue({ data: { data: [] } } as any);
        vi.mocked(evalApi.getBadCases).mockResolvedValue({ data: { data: [] } } as any);
        vi.mocked(knowledgeApi.listKBs).mockResolvedValue({ data: { data: [] } } as any);
    });

    it('hides 生成测试集 button without evaluation:run permission', async () => {
        allowButtonAccess = false;
        vi.mocked(useAuthStore).mockImplementation((selector: any) =>
            selector({ hasAccess: () => false }),
        );

        render(
            <MemoryRouter>
                <EvalPage />
            </MemoryRouter>,
        );

        await waitFor(() => {
            expect(evalApi.getTestsets).toHaveBeenCalledTimes(1);
        });

        expect(screen.queryByRole('button', { name: '生成测试集' })).not.toBeInTheDocument();
    });

    it('shows 生成测试集 button with evaluation:run permission', async () => {
        allowButtonAccess = true;
        vi.mocked(useAuthStore).mockImplementation((selector: any) =>
            selector({ hasAccess: () => true }),
        );

        render(
            <MemoryRouter>
                <EvalPage />
            </MemoryRouter>,
        );

        await waitFor(() => {
            expect(evalApi.getTestsets).toHaveBeenCalledTimes(1);
        });

        expect(screen.getByRole('button', { name: '生成测试集' })).toBeInTheDocument();
    });
});
