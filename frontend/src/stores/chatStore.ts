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
import type { ChatMessage, ConversationListItem, ChatContext, AIAction } from '../types';

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

interface ChatState {
    // === Panel 状态 ===
    /** Chat Panel 展开/折叠 */
    panelOpen: boolean;
    /** Panel 宽度 (px) */
    panelWidth: number;

    // === 上下文 ===
    /** 当前页面上下文 */
    context: ChatContext;

    // === 对话数据 ===
    currentConversationId: string | null;
    conversations: ConversationListItem[];
    messages: ChatMessage[];
    isGenerating: boolean;

    // === Actions: Panel ===
    togglePanel: () => void;
    setPanelOpen: (open: boolean) => void;
    setPanelWidth: (width: number) => void;

    // === Actions: Context ===
    /** 页面切换时更新上下文 (由 AppLayout 自动调用) */
    updateContext: (pathname: string) => void;

    // === Actions: 对话 ===
    setCurrentConversation: (id: string | null) => void;
    addMessage: (message: ChatMessage) => void;
    updateLastMessage: (content: string) => void;
    appendStatusToLastMessage: (status: string) => void;
    setGenerating: (value: boolean) => void;
    clearMessages: () => void;
    rateMessage: (messageId: string, rating: number) => void;
    loadConversations: () => Promise<void>;
    loadConversationDetails: (id: string) => Promise<void>;
    deleteConversation: (id: string) => Promise<void>;
    startNewChat: () => void;

    // === Knowledge Base Selection ===
    selectedKnowledgeBases: string[];
    toggleKnowledgeBase: (id: string) => void;
    setSelectedKnowledgeBases: (ids: string[]) => void;

    // === Actions: AI 操作 ===
    /** 执行 AI 操作 (由 ActionButton 触发，返回导航目标) */
    executeAction: (action: AIAction) => string | null;
}

export const useChatStore = create<ChatState>((set) => ({
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
        if (list.includes(id)) {
            return { selectedKnowledgeBases: list.filter(kb => kb !== id) };
        } else {
            return { selectedKnowledgeBases: [...list, id] };
        }
    }),
    setSelectedKnowledgeBases: (ids) => set({ selectedKnowledgeBases: ids }),

    // 对话数据
    currentConversationId: null,
    conversations: [],
    messages: [],
    isGenerating: false,

    // Panel Actions
    togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
    setPanelOpen: (open) => set({ panelOpen: open }),
    setPanelWidth: (width) => set({ panelWidth: Math.max(320, Math.min(600, width)) }),

    // Context Actions
    updateContext: (pathname) => {
        // 匹配路由到上下文
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
    rateMessage: (id, rating) =>
        set((state) => ({
            messages: state.messages.map((m) =>
                m.id === id ? { ...m, rating } : m
            ),
        })),

    loadConversations: async () => {
        try {
            const { chatApi } = await import('../services/chatApi');
            const res = await chatApi.getConversations();
            set({ conversations: res.data });
        } catch (error) {
            console.error('Failed to load conversations', error);
        }
    },

    loadConversationDetails: async (id) => {
        try {
            const { chatApi } = await import('../services/chatApi');
            const res = await chatApi.getConversation(id);
            set({
                currentConversationId: id,
                messages: res.data.messages.map((m: any) => ({
                    id: m.id,
                    role: m.role,
                    content: m.content,
                    created_at: m.created_at,
                    metadata: m.metadata ? JSON.parse(m.metadata) : undefined
                }))
            });
        } catch (error) {
            console.error('Failed to load conversation details', error);
        }
    },

    deleteConversation: async (id) => {
        try {
            const { chatApi } = await import('../services/chatApi');
            await chatApi.deleteConversation(id);
            set((state) => ({
                conversations: state.conversations.filter((c) => c.id !== id),
                currentConversationId: state.currentConversationId === id ? null : state.currentConversationId,
                messages: state.currentConversationId === id ? [] : state.messages
            }));
        } catch (error) {
            console.error('Failed to delete conversation', error);
        }
    },

    startNewChat: () => {
        set({
            currentConversationId: null,
            messages: []
        });
    },

    // AI 操作执行
    executeAction: (action) => {
        switch (action.type) {
            case 'navigate':
                // 返回导航目标，由组件侧调用 navigate()
                return action.target;
            case 'open_modal':
                // TODO: 触发全局 modal 事件
                console.log('[AI Action] Open modal:', action.target);
                return null;
            case 'execute':
                // TODO: 调用后端 API
                console.log('[AI Action] Execute:', action.target);
                return null;
            case 'suggest':
                return null;
            case 'show_data':
                // TODO: 在 chat 中内联展示数据
                console.log('[AI Action] Show data:', action.target);
                return null;
            default:
                return null;
        }
    },
}));
