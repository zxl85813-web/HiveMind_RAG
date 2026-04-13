/**
 * Chat Store — AI-First 核心状态管理。
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { ChatMessage, ChatContext, AIAction } from '../types';

export interface ClientEvent {
    name: string;
    data: string;
    timestamp: string;
}

/** 页面路由 → 上下文映射 */
const PAGE_CONTEXT_MAP: Record<string, Omit<ChatContext, 'currentPage'>> = {
    '/': {
        pageTitle: '概览',
        availableActions: [
            { type: 'navigate', label: '创建知识库', target: '/knowledge', icon: 'DatabaseOutlined', variant: 'primary' },
            { type: 'navigate', label: '查看 Agent', target: '/agents', icon: 'ClusterOutlined' },
        ],
    },
    '/knowledge': {
        pageTitle: '知识库管理',
        availableActions: [
            { type: 'open_modal', label: '创建知识库', target: 'create_kb', icon: 'PlusOutlined', variant: 'primary' },
            { type: 'execute', label: '上传文档', target: 'upload_doc', icon: 'UploadOutlined' },
        ],
    },
    '/agents': {
        pageTitle: 'Agent 蜂巢监控',
        availableActions: [
            { type: 'show_data', label: '查看 TODO 列表', target: 'agent_todos', icon: 'UnorderedListOutlined' },
            { type: 'show_data', label: '查看自省日志', target: 'reflection_log', icon: 'ExperimentOutlined' },
        ],
    },
    '/learning': {
        pageTitle: '技术动态',
        availableActions: [
            { type: 'open_modal', label: '添加订阅', target: 'add_subscription', icon: 'PlusOutlined', variant: 'primary' },
        ],
    },
    '/settings': {
        pageTitle: '系统设置',
        availableActions: [],
    },
};

/** 视图模式: 'ai' = 对话为中心, 'classic' = 传统 Dashboard */
export type ViewMode = 'ai' | 'classic';

interface ChatState {
    viewMode: ViewMode;
    toggleViewMode: () => void;
    setViewMode: (mode: ViewMode) => void;
    panelOpen: boolean;
    panelWidth: number;
    context: ChatContext;
    currentConversationId: string | null;
    messages: ChatMessage[];
    isGenerating: boolean;
    togglePanel: () => void;
    setPanelOpen: (open: boolean) => void;
    setPanelWidth: (width: number) => void;
    updateContext: (pathname: string) => void;
    setCurrentConversation: (id: string | null) => void;
    setMessages: (messages: ChatMessage[]) => void;
    addMessage: (message: ChatMessage) => void;
    updateLastMessage: (content: string) => void;
    updateLastMessageMetadata: (meta: Record<string, unknown>) => void;
    appendStatusToLastMessage: (status: string) => void;
    setGenerating: (value: boolean) => void;
    clearMessages: () => void;
    rateMessage: (messageId: string, rating: number) => void;
    setActionsToLastMessage: (actions: AIAction[]) => void;
    startNewChat: () => void;
    selectedKnowledgeBases: string[];
    toggleKnowledgeBase: (id: string) => void;
    setSelectedKnowledgeBases: (ids: string[]) => void;
    executeAction: (action: AIAction) => string | null;
    isCreateKBModalOpen: boolean;
    setCreateKBModalOpen: (open: boolean) => void;
    clientEvents: ClientEvent[];
    logEvent: (name: string, data?: unknown) => void;
    clearEvents: () => void;
}

export const useChatStore = create<ChatState>()(
    persist(
        (set) => ({
            viewMode: 'ai' as ViewMode,
            toggleViewMode: () => set((state) => ({ viewMode: state.viewMode === 'ai' ? 'classic' : 'ai' })),
            setViewMode: (mode) => set({ viewMode: mode }),
            panelOpen: true,
            panelWidth: 420,
            context: {
                currentPage: '/',
                pageTitle: '概览',
                availableActions: [],
            },
            selectedKnowledgeBases: [],
            toggleKnowledgeBase: (id) => set((state) => {
                const list = state.selectedKnowledgeBases;
                const newState = list.includes(id)
                    ? { selectedKnowledgeBases: list.filter(kb => kb !== id) }
                    : { selectedKnowledgeBases: [...list, id] };
                return { ...newState };
            }),
            setSelectedKnowledgeBases: (ids) => set({ selectedKnowledgeBases: ids }),
            isCreateKBModalOpen: false,
            setCreateKBModalOpen: (open) => set({ isCreateKBModalOpen: open }),
            clientEvents: [],
            logEvent: (name, data) => set((state) => ({
                clientEvents: [...state.clientEvents, {
                    name,
                    data: typeof data === 'string' ? data : JSON.stringify(data),
                    timestamp: new Date().toISOString()
                }]
            })),
            clearEvents: () => set({ clientEvents: [] }),
            currentConversationId: null,
            messages: [],
            isGenerating: false,
            togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
            setPanelOpen: (open) => set({ panelOpen: open }),
            setPanelWidth: (width) => set({ panelWidth: Math.max(320, Math.min(600, width)) }),
            updateContext: (pathname) => {
                const base = '/' + (pathname.split('/')[1] || '');
                const contextData = PAGE_CONTEXT_MAP[base] || PAGE_CONTEXT_MAP['/']!;
                set({
                    context: {
                        currentPage: pathname,
                        pageTitle: contextData.pageTitle,
                        availableActions: contextData.availableActions,
                    },
                });
            },
            setCurrentConversation: (id) => set({ currentConversationId: id }),
            setMessages: (messages) => set({ messages }),
            addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
            updateLastMessage: (content) => set((state) => {
                const msgs = [...state.messages];
                if (msgs.length > 0) msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content };
                return { messages: msgs };
            }),
            updateLastMessageMetadata: (meta) => set((state) => {
                const msgs = [...state.messages];
                if (msgs.length > 0) {
                    const lastMsg = msgs[msgs.length - 1];
                    msgs[msgs.length - 1] = { ...lastMsg, metadata: { ...(lastMsg.metadata || {}), ...meta } };
                }
                return { messages: msgs };
            }),
            appendStatusToLastMessage: (status) => set((state) => {
                const msgs = [...state.messages];
                if (msgs.length > 0) {
                    const lastMsg = msgs[msgs.length - 1];
                    const meta = lastMsg.metadata || {};
                    const statuses = meta.statuses || [];
                    msgs[msgs.length - 1] = { ...lastMsg, metadata: { ...meta, statuses: [...statuses, status] } };
                }
                return { messages: msgs };
            }),
            setGenerating: (value) => set({ isGenerating: value }),
            clearMessages: () => set({ messages: [] }),
            rateMessage: (id, rating) => set((state) => ({
                messages: state.messages.map((m) => m.id === id ? { ...m, rating } : m)
            })),
            setActionsToLastMessage: (actions) => set((state) => {
                const msgs = [...state.messages];
                if (msgs.length > 0) msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], actions };
                return { messages: msgs };
            }),
            startNewChat: () => set({ currentConversationId: null, messages: [] }),
            executeAction: (action) => {
                switch (action.type) {
                    case 'navigate':
                        set({ viewMode: 'classic' });
                        return action.target;
                    case 'open_modal':
                        if (action.target === 'create_kb') set({ isCreateKBModalOpen: true });
                        return null;
                    default:
                        return null;
                }
            },
        }),
        {
            name: 'hm-chat-storage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({ viewMode: state.viewMode }),
        }
    )
);
