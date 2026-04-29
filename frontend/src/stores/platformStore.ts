/**
 * Platform Store — 平台模式状态管理。
 *
 * 启动时从后端 /health 接口获取当前平台模式 (rag / agent / full)，
 * 前端据此动态显示/隐藏导航项、路由和快捷指令。
 *
 * @module stores
 */

import { create } from 'zustand';
import api from '../services/api';

export type PlatformMode = 'rag' | 'agent' | 'full';

interface PlatformModules {
    rag: boolean;
    agent: boolean;
}

interface PlatformState {
    /** 当前平台模式 */
    mode: PlatformMode;
    /** 各模块启用状态 */
    modules: PlatformModules;
    /** 是否已完成初始化加载 */
    loaded: boolean;
    /** 加载出错时的信息 */
    error: string | null;

    /** 便捷属性 */
    ragEnabled: boolean;
    agentEnabled: boolean;

    /** 从后端拉取平台模式 */
    fetchPlatformMode: () => Promise<void>;
}

export const usePlatformStore = create<PlatformState>((set) => ({
    mode: 'full',
    modules: { rag: true, agent: true },
    loaded: false,
    error: null,
    ragEnabled: true,
    agentEnabled: true,

    fetchPlatformMode: async () => {
        try {
            const res = await api.get('/health/');
            const { mode, modules } = res.data as {
                mode: PlatformMode;
                modules: PlatformModules;
            };
            set({
                mode,
                modules,
                ragEnabled: modules.rag,
                agentEnabled: modules.agent,
                loaded: true,
                error: null,
            });
        } catch (err: any) {
            // 如果 health 接口不可用，默认 full 模式
            console.warn('[PlatformStore] Failed to fetch platform mode, defaulting to full:', err.message);
            set({
                mode: 'full',
                modules: { rag: true, agent: true },
                ragEnabled: true,
                agentEnabled: true,
                loaded: true,
                error: err.message,
            });
        }
    },
}));
