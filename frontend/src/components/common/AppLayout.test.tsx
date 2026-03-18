import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AppLayout } from './AppLayout';
import { MemoryRouter } from 'react-router-dom';
import { useChatStore } from '../../stores/chatStore';

// Mock antd App to provide message/notification
vi.mock('antd', async () => {
    const actual = await vi.importActual('antd');
    return {
        ...actual,
        App: {
            useApp: () => ({
                message: { success: vi.fn(), error: vi.fn() },
                notification: { success: vi.fn(), error: vi.fn() },
            }),
        },
    };
});

// Mock stores and hooks
vi.mock('../../stores/chatStore', () => ({
    useChatStore: Object.assign(vi.fn(), {
        getState: vi.fn(() => ({
            setViewMode: vi.fn(),
        }))
    }),
}));

// Mock sub-components to avoid complex dependencies
vi.mock('../chat/ChatPanel', () => ({
    ChatPanel: () => <div data-testid="chat-panel">Chat Panel</div>
}));

vi.mock('../knowledge/CreateKBModal', () => ({
    CreateKBModal: () => <div data-testid="create-kb-modal">Create KB Modal</div>
}));

vi.mock('../../hooks/useDashboardData', () => ({
    useCreateKnowledgeBase: () => ({
        mutateAsync: vi.fn(),
    }),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key: string) => key,
        i18n: { language: 'zh-CN', changeLanguage: vi.fn() },
    }),
    initReactI18next: {
        type: '3rdParty',
        init: vi.fn(),
    },
}));

describe('AppLayout Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    const mockValues = {
        viewMode: 'classic',
        toggleViewMode: vi.fn(),
        panelOpen: true,
        panelWidth: 400,
        updateContext: vi.fn(),
        isCreateKBModalOpen: false,
        setCreateKBModalOpen: vi.fn(),
    };

    it('renders sidebar with navigation items in classic mode', () => {
        vi.mocked(useChatStore).mockReturnValue(mockValues as any);

        render(
            <MemoryRouter>
                <AppLayout />
            </MemoryRouter>
        );

        expect(screen.getByText('nav.dashboard')).toBeInTheDocument();
        expect(screen.getByText('nav.knowledge')).toBeInTheDocument();
    });

    it('hides sidebar in AI mode', () => {
        vi.mocked(useChatStore).mockReturnValue({
            ...mockValues,
            viewMode: 'ai',
        } as any);

        render(
            <MemoryRouter>
                <AppLayout />
            </MemoryRouter>
        );

        expect(screen.queryByText('nav.dashboard')).not.toBeInTheDocument();
        expect(screen.getByText('传统模式')).toBeInTheDocument();
    });
});
