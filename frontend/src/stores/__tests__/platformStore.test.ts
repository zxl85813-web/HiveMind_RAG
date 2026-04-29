/**
 * Platform Store 单元测试 — 验证平台模式状态管理。
 *
 * 测试覆盖:
 *   1. 默认状态 (full 模式)
 *   2. 从后端获取 rag 模式
 *   3. 从后端获取 agent 模式
 *   4. 后端不可用时降级为 full
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { usePlatformStore } from '../platformStore';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';

// axios baseURL 来自 .env: http://localhost:8000/api/v1
const API_BASE = 'http://localhost:8000/api/v1';

describe('platformStore', () => {
    beforeEach(() => {
        // 重置 store 到初始状态
        usePlatformStore.setState({
            mode: 'full',
            modules: { rag: true, agent: true },
            loaded: false,
            error: null,
            ragEnabled: true,
            agentEnabled: true,
        });
    });

    it('should have full mode as default', () => {
        const state = usePlatformStore.getState();
        expect(state.mode).toBe('full');
        expect(state.ragEnabled).toBe(true);
        expect(state.agentEnabled).toBe(true);
        expect(state.loaded).toBe(false);
    });

    it('should fetch and apply RAG mode from backend', async () => {
        server.use(
            http.get(`${API_BASE}/health/`, () => {
                return HttpResponse.json({
                    status: 'ok',
                    mode: 'rag',
                    modules: { rag: true, agent: false },
                });
            }),
        );

        await usePlatformStore.getState().fetchPlatformMode();

        const state = usePlatformStore.getState();
        expect(state.mode).toBe('rag');
        expect(state.ragEnabled).toBe(true);
        expect(state.agentEnabled).toBe(false);
        expect(state.loaded).toBe(true);
        expect(state.error).toBeNull();
    });

    it('should fetch and apply Agent mode from backend', async () => {
        server.use(
            http.get(`${API_BASE}/health/`, () => {
                return HttpResponse.json({
                    status: 'ok',
                    mode: 'agent',
                    modules: { rag: false, agent: true },
                });
            }),
        );

        await usePlatformStore.getState().fetchPlatformMode();

        const state = usePlatformStore.getState();
        expect(state.mode).toBe('agent');
        expect(state.ragEnabled).toBe(false);
        expect(state.agentEnabled).toBe(true);
        expect(state.loaded).toBe(true);
    });

    it('should fetch and apply Full mode from backend', async () => {
        server.use(
            http.get(`${API_BASE}/health/`, () => {
                return HttpResponse.json({
                    status: 'ok',
                    mode: 'full',
                    modules: { rag: true, agent: true },
                });
            }),
        );

        await usePlatformStore.getState().fetchPlatformMode();

        const state = usePlatformStore.getState();
        expect(state.mode).toBe('full');
        expect(state.ragEnabled).toBe(true);
        expect(state.agentEnabled).toBe(true);
        expect(state.loaded).toBe(true);
    });

    it('should fallback to full mode when backend is unavailable', async () => {
        server.use(
            http.get(`${API_BASE}/health/`, () => {
                return HttpResponse.error();
            }),
        );

        await usePlatformStore.getState().fetchPlatformMode();

        const state = usePlatformStore.getState();
        expect(state.mode).toBe('full');
        expect(state.ragEnabled).toBe(true);
        expect(state.agentEnabled).toBe(true);
        expect(state.loaded).toBe(true);
        expect(state.error).toBeTruthy();
    });
});
