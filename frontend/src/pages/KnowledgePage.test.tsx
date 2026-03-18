import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { KnowledgePage } from './KnowledgePage';
import { useAuthStore } from '../stores/authStore';
import { knowledgeApi } from '../services/knowledgeApi';

let allowButtonAccess = false;
let queryClient: QueryClient;

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

vi.mock('../services/knowledgeApi', () => ({
    knowledgeApi: {
        listKBs: vi.fn(),
        createKB: vi.fn(),
    },
}));

vi.mock('../components/common', () => ({
    PageContainer: ({ actions, children }: any) => (
        <div>
            <div data-testid="page-actions">{actions}</div>
            <div data-testid="page-content">{children}</div>
        </div>
    ),
    EmptyState: ({ action }: any) => <div data-testid="empty-state">{action}</div>,
    PermissionButton: ({ children, ...rest }: any) => {
        if (!allowButtonAccess) {
            return null;
        }
        return <button {...rest}>{children}</button>;
    },
}));

vi.mock('../components/knowledge/KnowledgeList', () => ({
    KnowledgeList: () => <div data-testid="knowledge-list" />,
}));

vi.mock('../components/knowledge/CreateKBModal', () => ({
    CreateKBModal: () => <div data-testid="create-kb-modal" />,
}));

vi.mock('../components/knowledge/KnowledgeDetail', () => ({
    KnowledgeDetail: () => <div data-testid="knowledge-detail" />,
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key: string) => key,
    }),
}));

describe('KnowledgePage Permission', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                    gcTime: 0,
                },
            },
        });
        vi.mocked(useAuthStore).mockReturnValue({
            hasAccess: vi.fn(),
            profile: { roles: [] },
        } as any);
        vi.mocked(knowledgeApi.listKBs).mockResolvedValue({ data: { data: [] } } as any);
    });

    it('hides create action for viewer without knowledge:manage', async () => {
        allowButtonAccess = false;
        vi.mocked(useAuthStore).mockImplementation((selector: any) => selector({
            hasAccess: () => false,
        }));

        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <KnowledgePage />
                </MemoryRouter>
            </QueryClientProvider>,
        );

        await waitFor(() => {
            expect(knowledgeApi.listKBs).toHaveBeenCalledTimes(1);
        });

        expect(screen.queryByRole('button', { name: 'common.create' })).not.toBeInTheDocument();
    });

    it('shows create action for role with knowledge:manage', async () => {
        allowButtonAccess = true;
        vi.mocked(useAuthStore).mockImplementation((selector: any) => selector({
            hasAccess: () => true,
        }));

        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <KnowledgePage />
                </MemoryRouter>
            </QueryClientProvider>,
        );

        await waitFor(() => {
            expect(knowledgeApi.listKBs).toHaveBeenCalledTimes(1);
        });

        expect(screen.getAllByRole('button', { name: 'common.create' }).length).toBeGreaterThan(0);
    });
});