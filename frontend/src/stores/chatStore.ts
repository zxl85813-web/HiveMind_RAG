/**
 * Chat Store — AI-First 核心状态管理。
 *
 * 不只管消息，还管:
 *   - Chat Panel 展开/折叠
 *   - 当前页面上下文 (AI 感知用户在哪)
 *   - AI 操作执行队列
 *
 * @module stores
 * @see docs/design/ai-first-frontend.md
 * @see REGISTRY.md > 前端 > Stores > chatStore
 */

import { create } from 'zustand';
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
    // === 视图模式 ===
    viewMode: ViewMode;
    toggleViewMode: () => void;
    setViewMode: (mode: ViewMode) => void;

    // === Panel 状态 ===
    panelOpen: boolean;
    panelWidth: number;

    // === 上下文 ===
    context: ChatContext;

    // === 对话数据 (仅限活跃会话缓存) ===
    currentConversationId: string | null;
    messages: ChatMessage[];
    isGenerating: boolean;

    // === Actions: Panel ===
    togglePanel: () => void;
    setPanelOpen: (open: boolean) => void;
    setPanelWidth: (width: number) => void;

    // === Actions: Context ===
    updateContext: (pathname: string) => void;

    // === Actions: 对话 (UI 侧操作) ===
    setCurrentConversation: (id: string | null) => void;
    setMessages: (messages: ChatMessage[]) => void;
    addMessage: (message: ChatMessage) => void;
    updateLastMessage: (content: string) => void;
    updateLastMessageMetadata: (meta: any) => void;
    appendStatusToLastMessage: (status: string) => void;
    setGenerating: (value: boolean) => void;
    clearMessages: () => void;
    rateMessage: (messageId: string, rating: number) => void;
    setActionsToLastMessage: (actions: AIAction[]) => void;
    startNewChat: () => void;

    // === Knowledge Base Selection ===
    selectedKnowledgeBases: string[];
    toggleKnowledgeBase: (id: string) => void;
    setSelectedKnowledgeBases: (ids: string[]) => void;

    // === Actions: AI 操作 ===
    executeAction: (action: AIAction) => string | null;

    // === UI State: Modals ===
    isCreateKBModalOpen: boolean;
    setCreateKBModalOpen: (open: boolean) => void;

    // === Client Event Logging ===
    clientEvents: ClientEvent[];
    logEvent: (name: string, data?: any) => void;
    clearEvents: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
    // 视图模式
    viewMode: 'ai' as ViewMode,
    toggleViewMode: () => set((state) => ({ viewMode: state.viewMode === 'ai' ? 'classic' : 'ai' })),
    setViewMode: (mode) => set({ viewMode: mode }),

    // Panel 状态
    panelOpen: true,
    panelWidth: 420,

    // 上下文
    context: {
        currentPage: '/',
        pageTitle: '概览',
        availableActions: [],
    },

    // Knowledge Base Selection
    selectedKnowledgeBases: [],
    toggleKnowledgeBase: (id) => set((state) => {
        const list = state.selectedKnowledgeBases;
        const newState = list.includes(id)
            ? { selectedKnowledgeBases: list.filter(kb => kb !== id) }
            : { selectedKnowledgeBases: [...list, id] };

        const isSelected = !list.includes(id);
        const eventName = isSelected ? "Select KB" : "Unselect KB";
        const events = [...state.clientEvents, {
            name: eventName,
            data: `KB ID: ${id}`,
            timestamp: new Date().toISOString()
        }];

        return { ...newState, clientEvents: events };
    }),
    setSelectedKnowledgeBases: (ids) => set({ selectedKnowledgeBases: ids }),

    // UI State: Modals
    isCreateKBModalOpen: false,
    setCreateKBModalOpen: (open) => set({ isCreateKBModalOpen: open }),

    // Client Events
    clientEvents: [],
    logEvent: (name, data) => set((state) => ({
        clientEvents: [...state.clientEvents, {
            name,
            data: typeof data === 'string' ? data : JSON.stringify(data),
            timestamp: new Date().toISOString()
        }]
    })),
    clearEvents: () => set({ clientEvents: [] }),

    // 对话数据
    currentConversationId: null,
    messages: [],
    isGenerating: false,

    // Panel Actions
    togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
    setPanelOpen: (open) => set({ panelOpen: open }),
    setPanelWidth: (width) => set({ panelWidth: Math.max(320, Math.min(600, width)) }),

    // Context Actions
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

    // 对话 Actions
    setCurrentConversation: (id) => set({ currentConversationId: id }),
    setMessages: (messages) => set({ messages }),
    addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
    updateLastMessage: (content) =>
        set((state) => {
            const msgs = [...state.messages];
            if (msgs.length > 0) {
                msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content };
            }
            return { messages: msgs };
        }),
    updateLastMessageMetadata: (meta: any) =>
        set((state) => {
            const msgs = [...state.messages];
            if (msgs.length > 0) {
                const lastMsg = msgs[msgs.length - 1];
                msgs[msgs.length - 1] = {
                    ...lastMsg,
                    metadata: { ...(lastMsg.metadata || {}), ...meta }
                };
            }
            return { messages: msgs };
        }),
    appendStatusToLastMessage: (status) =>
        set((state) => {
            const msgs = [...state.messages];
            if (msgs.length > 0) {
                const lastMsg = msgs[msgs.length - 1];
                const meta = lastMsg.metadata || {};
                const statuses = meta.statuses || [];
                msgs[msgs.length - 1] = {
                    ...lastMsg,
                    metadata: { ...meta, statuses: [...statuses, status] }
                };
            }
            return { messages: msgs };
        }),
    setGenerating: (value) => set({ isGenerating: value }),
    clearMessages: () => set({ messages: [] }),
    rateMessage: (id, rating) => {
        set((state) => {
            const events = [...state.clientEvents, {
                name: "Message Feedback",
                data: `ID: ${id}, Rating: ${rating}`,
                timestamp: new Date().toISOString()
            }];
            return {
                messages: state.messages.map((m) =>
                    m.id === id ? { ...m, rating } : m
                ),
                clientEvents: events
            };
        });
    },
    setActionsToLastMessage: (actions) =>
        set((state) => {
            const msgs = [...state.messages];
            if (msgs.length > 0) {
                msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], actions };
            }
            return { messages: msgs };
        }),

    startNewChat: () => {
        set({
            currentConversationId: null,
            messages: []
        });
    },

    // AI 操作执行
    executeAction: (action) => {
        set((state) => ({
            clientEvents: [...state.clientEvents, {
                name: "Execute Action",
                data: `Type: ${action.type}, Label: ${action.label}, Target: ${action.target}`,
                timestamp: new Date().toISOString()
            }]
        }));

        switch (action.type) {
            case 'navigate':
                set({ viewMode: 'classic' });
                return action.target;
            case 'open_modal':
                if (action.target === 'create_kb') {
                    set({ isCreateKBModalOpen: true });
                }
                return null;
            case 'execute':
                set((state) => {
                    const msgs = [...state.messages];
                    if (msgs.length > 0) {
                        const lastMsg = msgs[msgs.length - 1];
                        const meta = lastMsg.metadata || {};
                        const statuses = meta.statuses || [];
                        msgs[msgs.length - 1] = {
                            ...lastMsg,
                            metadata: { ...meta, statuses: [...statuses, `任务已启动: ${action.label}`] }
                        };
                    }
                    return { messages: msgs };
                });
                return null;
            case 'suggest':
            case 'show_data':
                return null;
            default:
                return null;
        }
    },
}));
