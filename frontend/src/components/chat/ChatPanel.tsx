/**
 * 🛰️ [Architecture-Gate]: ChatPanel — AI-First 架构核心 (重构完结版)
 */

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { App, Flex, Typography, Tooltip, Tag, Space, Avatar, Popover, Modal, Timeline, theme } from 'antd';
import { Bubble, Sender, Prompts, ThoughtChain, Welcome, Conversations, Actions, CodeHighlighter } from '@ant-design/x';
import { useXChat } from '@ant-design/x-sdk';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';
import {
    RobotOutlined,
    UserOutlined,
    CompressOutlined,
    EnvironmentOutlined,
    LikeOutlined,
    DislikeOutlined,
    LikeFilled,
    DislikeFilled,
    HistoryOutlined,
    PlusOutlined,
} from '@ant-design/icons';

import { useChatStore } from '../../stores/chatStore';
import { ActionButton } from './ActionButton';
import { intentManager } from '../../core/IntentManager';
import { chatApi } from '../../services/chatApi';
import { GraphVisualizer } from '../knowledge/GraphVisualizer';
import { matchQuickCommand } from '../../config/quickCommands';
import { 
    useConversationsQuery as useConversations, 
    useConversationDetailQuery as useConversationDetails, 
    useSubmitFeedbackMutation as useSubmitFeedback 
} from '../../hooks/queries/useChatQuery';
import styles from './ChatPanel.module.css';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;

export const ChatPanel: React.FC = () => {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { token } = theme.useToken();
    const {
        viewMode,
        panelOpen,
        togglePanel,
        context,
        currentConversationId,
        setCurrentConversation,
        selectedKnowledgeBases,
        startNewChat: resetStoreChat
    } = useChatStore();

    // === React Query Hooks ===
    const { data: conversations, refetch: refetchConversations } = useConversations();
    const { data: historyMessages } = useConversationDetails(currentConversationId);
    const feedbackMutation = useSubmitFeedback();

    // === X-Chat Hook ===
    // v2.x useXChat hook usage
    const { messages, setMessages, setMessage } = useXChat({} as any);

    // 当 historyMessages 加载完成后，同步到 x-chat
    useEffect(() => {
        const hDetail = historyMessages as any;
        if (hDetail?.messages && hDetail.messages.length > 0) {
            setMessages(hDetail.messages.map((m: any) => ({
                id: m.id,
                message: m.content,
                status: 'success',
                role: m.role,
                metadata: m.metadata || {
                    prompt_tokens: m.prompt_tokens,
                    completion_tokens: m.completion_tokens,
                    total_tokens: m.total_tokens,
                    latency_ms: m.latency_ms,
                    is_cached: m.is_cached,
                    trace_data: m.trace_data
                },
                rating: m.rating,
                created_at: m.created_at
            })));
        } else if (!currentConversationId) {
            setMessages([]);
        }
    }, [historyMessages, currentConversationId, setMessages]);

    // === 内部状态 ===
    const [inputValue, setInputValue] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [isGraphModalOpen, setIsGraphModalOpen] = useState(false);
    const [graphData] = useState<any>(null);
    const [isTraceModalOpen, setIsTraceModalOpen] = useState(false);
    const [currentTrace] = useState<any[]>([]);
    const [isCitationModalOpen, setIsCitationModalOpen] = useState(false);
    const [citationModalText, setCitationModalText] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const citationRegex = /\[(\d+)\]/g;
    const extractCitationIndexes = (content: string) => {
        const indices = new Set<number>();
        let match: RegExpExecArray | null = null;
        while ((match = citationRegex.exec(content)) !== null) {
            indices.add(Number(match[1]));
        }
        return Array.from(indices).sort((a, b) => a - b);
    };

    /** 滚动触底 */
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    /** 处理反馈 */
    const handleFeedback = (msgId: string, rating: number) => {
        feedbackMutation.mutate({ messageId: msgId, rating });
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, rating } : m));
    };

    /** 快速命令匹配 */
    const tryQuickCommand = (input: string): boolean => {
        const cmd = matchQuickCommand(input);
        if (!cmd) return false;

        setMessages(prev => [
            ...prev,
            { id: `usr-${Date.now()}`, role: 'user', message: input, status: 'success' },
            { id: `ast-${Date.now()}`, role: 'assistant', message: cmd.reply, status: 'success', metadata: { actions: cmd.actions } }
        ]);
        return true;
    };

    /** 发送消息入口 */
    const handleSend = async (value: string) => {
        if (!value.trim() || isGenerating) return;
        setInputValue('');

        if (tryQuickCommand(value)) return;

        // 1. 添加用户消息
        const userMsgId = `usr-${Date.now()}`;
        setMessages(prev => [...prev, { id: userMsgId, role: 'user', message: value, status: 'success' }]);

        // 2. 准备 AI 消息占位
        const assistantMsgId = `ast-${Date.now()}`;
        setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', message: '', status: 'loading' }]);

        setIsGenerating(true);
        let fullContent = '';
        const statuses: string[] = [];

        try {
            await chatApi.streamChat({
                message: value,
                conversationId: currentConversationId,
                knowledgeBaseIds: selectedKnowledgeBases,
                onDelta: (delta) => {
                    fullContent += delta;

                    const actionRegex = /\[ACTION:\s*({.*?})\]/g;
                    let match;
                    const foundActions: any[] = [];
                    let displayContent = fullContent;

                    while ((match = actionRegex.exec(fullContent)) !== null) {
                        try {
                            const actionData = JSON.parse(match[1]);
                            foundActions.push(actionData);
                            displayContent = displayContent.replace(match[0], '');
                        } catch { /* partial */ }
                    }

                    setMessage(assistantMsgId, {
                        message: displayContent.trim(),
                        extraInfo: foundActions.length > 0 ? { actions: foundActions } : undefined
                    });
                },
                onStatus: (status) => {
                    const tagMatch = status.match(/Tags: \[(.*?)\\]/);
                    if (tagMatch && tagMatch[1]) {
                        // Tags are currently just logged/extracted but not displayed in graph
                    } else {
                        statuses.push(status);
                        const thoughtChainItems = statuses.map((s, index) => {
                            let title = s;
                            let content = undefined;

                            if (s.includes('🤔') || s.includes('💡') || s.includes('💭') || s.includes('⚡')) {
                                title = s;
                            } else if (s.startsWith('<think>')) {
                                title = '🤔 内部思考';
                                content = s.replace(/<\/?think>/g, '').trim();
                            } else {
                                title = `⚡ ${s}`;
                            }
                            return {
                                key: `thought-${index}`,
                                title,
                                content,
                                status: 'success'
                            };
                        });

                        setMessages((prev: any[]) => prev.map(m => m.id === assistantMsgId ? { ...m, metadata: { ...(m.metadata || {}), thoughtChain: thoughtChainItems } } : m));
                    }
                },
                onSessionCreated: (id) => {
                    setCurrentConversation(id);
                    refetchConversations();
                },
                onFinish: (metrics) => {
                    setIsGenerating(false);
                    setMessage(assistantMsgId, {
                        status: 'success',
                        extraInfo: { ...metrics }
                    });
                    refetchConversations();
                },
                onError: (err: any) => {
                    setIsGenerating(false);
                    setMessage(assistantMsgId, {
                        status: 'error',
                        message: '无法连接到 AI 服务，请检查网络。'
                    });
                    message.error(err.message || '对话出错');
                }
            });
        } catch (e: unknown) {
            console.error(e);
            setIsGenerating(false);
            setMessage(assistantMsgId, { status: 'error' });
        }
    };


    const safeConversations = useMemo(() => {
        if (Array.isArray(conversations)) return conversations;
        const payload = conversations as any;
        if (Array.isArray(payload?.data)) return payload.data;
        if (Array.isArray(payload?.items)) return payload.items;
        return [];
    }, [conversations]);

    const historyContent = (
        <div style={{ width: 280, maxHeight: 400, overflowY: 'auto', padding: '4px 0' }}>
            <Conversations
                items={safeConversations.map((item: any) => ({
                    key: item.id,
                    className: styles.historyItem,
                    label: (
                        <div 
                            onMouseEnter={() => intentManager.predict('chat', { id: item.id })}
                            onMouseLeave={() => intentManager.cancel('chat', { id: item.id })}
                            style={{ width: '100%' }}
                            data-testid="conversation-item"
                        >
                            {item.title}
                        </div>
                    ),
                    description: item.last_message_preview,
                }))}
                activeKey={currentConversationId || undefined}
                onActiveChange={(key) => setCurrentConversation(key)}
            />
        </div>
    );

    const contextPrompts = useMemo(() =>
        context.availableActions.slice(0, 3).map((action: any) => ({
            key: action.target,
            label: action.label,
            description: (action.type === 'navigate' ? '跳转到' : '') + action.label,
        })), [context.availableActions]);

    if (!panelOpen) {
        return (
            <div className={styles.collapsed} onClick={togglePanel}>
                <Tooltip title="展开 AI 助手" placement="left">
                    <RobotOutlined className={styles.collapsedIcon} />
                </Tooltip>
            </div>
        );
    }

    return (
        <div className={styles.panel}>
            <Flex align="center" justify="space-between" className={styles.panelHeader + (viewMode === 'ai' ? ' ' + styles.headerAI : '')}>
                <Flex align="center" gap={8}>
                    <RobotOutlined className={styles.headerIcon} />
                    <Text strong>{t('chat.title')}</Text>
                    <Tag icon={<EnvironmentOutlined />} color="processing">{context.pageTitle}</Tag>
                </Flex>
                <Space size={8}>
                    <Popover content={historyContent} title={t('chat.history')} trigger="click" placement="bottomRight">
                        <HistoryOutlined className={styles.headerAction} data-testid="history-button" />
                    </Popover>
                    <PlusOutlined className={styles.headerAction} onClick={resetStoreChat} />
                    <CompressOutlined className={styles.headerAction} onClick={togglePanel} />
                </Space>
            </Flex>

            <div className={styles.messagesArea}>
                {messages.length === 0 ? (
                    <div className={styles.emptyState}>
                        <Welcome
                            variant="borderless"
                            icon={<div className={styles.emptyIcon}>⬡</div>}
                            title="HiveMind AI"
                            description={`当前在「${context.pageTitle}」页面，有什么可以帮你的？`}
                        />
                        {contextPrompts.length > 0 && (
                            <Prompts items={contextPrompts} onItemClick={(info) => { if (info.data.description) handleSend(info.data.description as string); }} wrap className={styles.contextPrompts} />
                        )}
                    </div>
                ) : (
                    <Bubble.List
                        items={messages.map((msg: any, idx) => {
                            const isUser = msg.role === 'user';
                            const loading = msg.status === 'loading';
                            return {
                                key: msg.id || String(idx),
                                role: isUser ? 'end' : 'start',
                                className: isUser ? 'chat-message user' : 'chat-message assistant',
                                avatar: isUser ? <Avatar icon={<UserOutlined />} style={{ background: token.colorPrimary }} /> : <Avatar icon={<RobotOutlined />} style={{ background: token.colorBgElevated }} />,
                                loading: loading && !msg.message,
                                content: (
                                    <Flex vertical gap={8}>
                                        {msg.metadata?.thoughtChain && msg.metadata.thoughtChain.length > 0 && (
                                            <ThoughtChain items={msg.metadata.thoughtChain} />
                                        )}
                                        <div className={styles.markdownBody}>
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                rehypePlugins={[rehypeHighlight]}
                                                components={{
                                                    code({ inline, className, children, ...props }: any) {
                                                        const match = /language-(\w+)/.exec(className || '');
                                                        return !inline && match ? (
                                                            <CodeHighlighter lang={match[1]} {...props}>
                                                                {String(children).replace(/\n$/, '')}
                                                            </CodeHighlighter>
                                                        ) : (
                                                            <code className={className} {...props}>
                                                                {children}
                                                            </code>
                                                        );
                                                    }
                                                }}
                                            >
                                                {msg.message || (loading ? '...' : '')}
                                            </ReactMarkdown>
                                        </div>
                                        {msg.role === 'assistant' && msg.message && (
                                            <Flex gap={6} wrap>
                                                {extractCitationIndexes(String(msg.message)).map((idx) => {
                                                    const source = msg.metadata?.sources?.[idx - 1];
                                                    return (
                                                        <Tag
                                                            key={`cite-tag-${msg.id}-${idx}`}
                                                            color="blue"
                                                            style={{ cursor: source ? 'pointer' : 'default' }}
                                                            onClick={source ? () => {
                                                                const text = [
                                                                    `[#${idx}] ${source.document_name || 'Unknown Source'}`,
                                                                    source.page_number ? `Page: ${source.page_number}` : null,
                                                                    source.chunk_content || '',
                                                                ].filter(Boolean).join('\n');
                                                                setCitationModalText(text);
                                                                setIsCitationModalOpen(true);
                                                            } : undefined}
                                                        >
                                                            [{idx}] {source?.document_name || 'Source unavailable'}
                                                        </Tag>
                                                    );
                                                })}
                                            </Flex>
                                        )}
                                        {msg.extraInfo?.actions && (
                                            <Flex gap={6} wrap>
                                                {msg.extraInfo.actions.map((action: any, i: number) => <ActionButton key={i} action={action} />)}
                                            </Flex>
                                        )}
                                        {msg.role === 'assistant' && msg.id && msg.id.indexOf('usr-') === -1 && !loading && (
                                            <Actions
                                                items={[
                                                    {
                                                        key: 'good',
                                                        icon: msg.rating === 1 ? <LikeFilled style={{ color: token.colorInfo }} /> : <LikeOutlined />,
                                                        onItemClick: () => handleFeedback(msg.id!, 1)
                                                    },
                                                    {
                                                        key: 'bad',
                                                        icon: msg.rating === -1 ? <DislikeFilled style={{ color: token.colorError }} /> : <DislikeOutlined />,
                                                        onItemClick: () => handleFeedback(msg.id!, -1)
                                                    }
                                                ]}
                                            />
                                        )}
                                    </Flex>
                                ),
                            };
                        })}
                    />
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className={styles.inputArea}>
                <Sender value={inputValue} onChange={setInputValue} onSubmit={handleSend} loading={isGenerating} placeholder={t('chat.placeholder')} />
            </div>

            <Modal title="记忆图谱 (Tier 2)" open={isGraphModalOpen} onCancel={() => setIsGraphModalOpen(false)} footer={null} width={800} styles={{ body: { height: 600, padding: 0, background: token.colorBgLayout } }} centered destroyOnHidden>
                {graphData && <GraphVisualizer data={graphData} width={800} height={600} />}
            </Modal>

            <Modal title="执行追踪" open={isTraceModalOpen} onCancel={() => setIsTraceModalOpen(false)} footer={null} width={650} centered>
                <Timeline items={(currentTrace || []).map((step) => ({
                    color: step.status === 'success' ? token.colorSuccess : token.colorInfo,
                    children: <Text strong>{step.name} ({step.duration_ms.toFixed(0)}ms)</Text>
                }))} />
            </Modal>

            <Modal
                title="引用片段"
                open={isCitationModalOpen}
                onCancel={() => setIsCitationModalOpen(false)}
                footer={null}
                width={720}
                centered
            >
                <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{citationModalText}</pre>
            </Modal>
        </div>
    );
};
