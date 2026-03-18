import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useDashboardStats } from '../useDashboardQuery';
import { agentApi } from '../../../services/agentApi';
import { knowledgeApi } from '../../../services/knowledgeApi';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock the APIs
vi.mock('../../../services/agentApi', () => ({
    agentApi: {
        getStats: vi.fn(),
    },
}));

vi.mock('../../../services/knowledgeApi', () => ({
    knowledgeApi: {
        listKBs: vi.fn(),
    },
}));

const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });
    return ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
};

describe('useDashboardStats Hook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should include total_discoveries in the returned stats', async () => {
        // Step 1: Mock return data
        // total_discoveries is currently NOT in the type, but let's mock it anyway
        vi.mocked(agentApi.getStats).mockResolvedValue({
            data: {
                success: true,
                data: {
                    active_agents: 5,
                    today_requests: 100,
                    shared_todos: 10,
                    reflection_logs: 50,
                    total_discoveries: 42, // The new field
                }
            }
        } as any);

        vi.mocked(knowledgeApi.listKBs).mockResolvedValue({
            data: {
                success: true,
                data: [{}, {}] // 2 KBs
            }
        } as any);

        const { result } = renderHook(() => useDashboardStats(), {
            wrapper: createWrapper(),
        });

        // Step 2: Assert expected data
        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data).toMatchObject({
            total_kbs: 2,
            active_agents: 5,
            total_discoveries: 42, // This should FAIL until implementation
        });
    });
});
