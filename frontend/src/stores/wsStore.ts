/**
 * WebSocket Store — 全局 WebSocket 连接状态管理 (Zustand)。
 *
 * @module stores
 * @see REGISTRY.md > 前端 > Stores > wsStore
 */

import { create } from 'zustand';
import type { ServerMessage } from '../types';

interface WSState {
    /** 连接状态 */
    connected: boolean;
    /** 最近收到的通知列表 */
    notifications: ServerMessage[];
    /** 未读通知数 */
    unreadCount: number;

    /** Actions */
    setConnected: (value: boolean) => void;
    addNotification: (msg: ServerMessage) => void;
    clearUnread: () => void;
}

export const useWSStore = create<WSState>((set) => ({
    connected: false,
    notifications: [],
    unreadCount: 0,

    setConnected: (value) => set({ connected: value }),
    addNotification: (msg) =>
        set((state) => ({
            notifications: [msg, ...state.notifications].slice(0, 100), // Keep latest 100
            unreadCount: state.unreadCount + 1,
        })),
    clearUnread: () => set({ unreadCount: 0 }),
}));
