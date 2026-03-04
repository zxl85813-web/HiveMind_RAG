/**
 * ChatPanel — AI 对话面板 (永驻右侧)。
 *
 * 这是 AI-First 架构的核心组件:
 *   - 始终显示在 layout 右侧 (可折叠)
 *   - 感知当前页面上下文
 *   - AI 回答中可嵌入 ActionButton
 *   - 上方显示上下文指示器
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { App, Flex, Typography, Tooltip, Tag, Space, Avatar, Popover, Checkbox, List, Modal, Collapse, Timeline } from 'antd';
import { Bubble, Sender, Prompts } from '@ant-design/x';
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
    DatabaseOutlined,
    HistoryOutlined,
    PlusOutlined,
    DeleteOutlined,
    CaretRightOutlined,
    ThunderboltOutlined,
    DashboardOutlined,
    DeploymentUnitOutlined,
    BugOutlined,
    ClockCircleOutlined,
    CheckCircleOutlined,
    ExclamationCircleOutlined,
    FileSearchOutlined
} from '@ant-design/icons';

import { useChatStore } from '../../stores/chatStore';
import { ActionButton } from './ActionButton';
import { chatApi } from '../../services/chatApi';
import { knowledgeApi } from '../../services/knowledgeApi';
import { memoryApi } from '../../services/memoryApi';
import { GraphVisualizer } from '../knowledge/GraphVisualizer';
import type { KnowledgeBase } from '../../types';
import { matchQuickCommand } from '../../config/quickCommands';
import styles from './ChatPanel.module.css';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;

export const ChatPanel: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const { message } = App.useApp();
    const {
        viewMode,
        panelOpen,
        togglePanel,
        context,
        messages,
        isGenerating,
        addMessage,
        setGenerating,
        rateMessage,
        selectedKnowledgeBases,
        setSelectedKnowledgeBases,
        conversations,
        loadConversations,
        loadConversationDetails,
        deleteConversation,
        startNewChat,
        currentConversationId,
        setCurrentConversation,
        executeAction
    } = useChatStore();

    const [inputValue, setInputValue] = useState('');
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [isGraphModalOpen, setIsGraphModalOpen] = useState(false);
    const [graphData, setGraphData] = useState<{ nodes: any[], links: any[] } | null>(null);
    const [radarTags, setRadarTags] = useState<string[]>([]);
    const [isTraceModalOpen, setIsTraceModalOpen] = useState(false);
    const [currentTrace, setCurrentTrace] = useState<any[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (panelOpen) {
            knowledgeApi.listKBs()
                .then(res => setKbs(res.data.data))
                .catch(err => console.error("Failed to load KBs", err));
            loadConversations();
        }
    }, [panelOpen]);

    /** 处理反馈 */
    const handleFeedback = (msgId: string, rating: number) => {
        rateMessage(msgId, rating);
        chatApi.submitFeedback(msgId, rating);
    };

    /** 处理建议点击 */
    const handlePromptClick = (action: any) => {
        const navTarget = executeAction(action);
        if (navTarget) {
            navigate(navTarget);
        }
    };

    /** 尝试匹配快速指令，匹配成功返回 true */
    const tryQuickCommand = (input: string): boolean => {
        const cmd = matchQuickCommand(input);
        if (!cmd) return false;
        // 1. 添加用户消息
        addMessage({
            id: `usr-${Date.now()}`,
            role: 'user',
            content: input,
            created_at: new Date().toISOString(),
        });
        // 2. 添加即时 AI 回复（含按钮）
        addMessage({
            id: `ast-${Date.now()}`,
            role: 'assistant',
            content: cmd.reply,
            actions: cmd.actions,
            created_at: new Date().toISOString(),
            metadata: { is_cached: false, latency_ms: 0 },
        });
        return true;
    };

    /** 发送消息 */
    const handleSend = async (value: string) => {
        if (!value.trim()) return;
        setInputValue('');
        setRadarTags([]);

        // === Quick Command 快速匹配 ===
        if (tryQuickCommand(value)) {
            // 匹配成功，直接返回，不走后端
            return;
        }

        // === 正常 AI 流程 ===
        setGenerating(true);

        const userMsgId = `usr-${Date.now()}`;
        addMessage({
            id: userMsgId,
            role: 'user',
            content: value,
            created_at: new Date().toISOString()
        });

        addMessage({
            id: `ast-${Date.now()}`,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
        });

        const chatStoreState = useChatStore.getState();
        const clientEvents = [...chatStoreState.clientEvents];
        chatStoreState.clearEvents();
        let fullContent = '';

        await chatApi.streamChat({
            message: value,
            conversationId: currentConversationId,
            knowledgeBaseIds: chatStoreState.selectedKnowledgeBases,
            clientEvents: clientEvents,
            onDelta: (delta) => {
                fullContent += delta;

                // ==========================================
                // 🛡️ [AI-LOCKED]: 流式信令解析区 (Action Parsing)
                // [设计意图]: 这段代码是实现“Agent 施放 UI 魔法按钮”的核心。
                // 后端会把控制指令（如跳出弹窗）混杂在 Markdown 文本流里发过来。
                // 这里的正则表达式提取和 replace 是为了将隐藏指令剥离，然后转交给 Zustand 去实例化 ActionButton。
                // [⚠️ 禁区]: 不要为了“代码更精简”把这个 while 循环删掉或随意修改正则，否则前端收到的 UI 指令将彻底崩盘。
                // ==========================================
                const actionRegex = /\[ACTION:\s*({.*?})\]/g;
                let match;
                const foundActions: any[] = [];
                let displayContent = fullContent;

                // Reset regex for each iteration to handle the growing string
                while ((match = actionRegex.exec(fullContent)) !== null) {
                    try {
                        const actionData = JSON.parse(match[1]);
                        foundActions.push(actionData);
                        // Hide it from the raw markdown text for a cleaner look
                        displayContent = displayContent.replace(match[0], '');
                    } catch (e) {
                        // Incomplete JSON during streaming, skip
                    }
                }

                useChatStore.getState().updateLastMessage(displayContent.trim());
                if (foundActions.length > 0) {
                    useChatStore.getState().setActionsToLastMessage(foundActions);
                }
            },
            onStatus: (status) => {
                useChatStore.getState().appendStatusToLastMessage(status);
                const match = status.match(/Tags: \[(.*?)\]/);
                if (match && match[1]) {
                    const tags = match[1].split(',').map(t => t.trim());
                    setRadarTags(prev => [...new Set([...prev, ...tags])]);
                }
            },
            onInsight: (insight) => {
                // Update the last message with proactive actions from the Insight Engine
                if (insight && insight.actions) {
                    useChatStore.getState().setActionsToLastMessage(insight.actions);
                }
            },
            onSessionCreated: (id) => {
                setCurrentConversation(id);
                loadConversations();
            },
            onFinish: (metrics) => {
                setGenerating(false);
                if (metrics) {
                    useChatStore.getState().updateLastMessageMetadata(metrics);
                }
                loadConversations();
            },
            onError: (err) => {
                console.error('Chat error:', err);
                fullContent += '\n[系统错误: 无法连接到 AI 服务]';
                useChatStore.getState().updateLastMessage(fullContent);
                setGenerating(false);
            }
        });
    };

    const contextPrompts = context.availableActions.slice(0, 3).map((action) => ({
        key: action.target,
        label: action.label,
        description: (action.type === 'navigate' ? '跳转到' : '') + action.label,
    }));

    if (!panelOpen) {
        return (
            <div className={styles.collapsed} onClick={togglePanel}>
                <Tooltip title="展开 AI 助手" placement="left">
                    <RobotOutlined className={styles.collapsedIcon} />
                </Tooltip>
            </div>
        );
    }

    const fetchRealGraph = async () => {
        if (radarTags.length === 0) return;
        try {
            const res = await memoryApi.getGraph(radarTags);
            if (res.data.nodes.length > 0) {
                setGraphData(res.data);
                setIsGraphModalOpen(true);
            } else {
                message.info("未找到关联图谱节点");
            }
        } catch (err) {
            console.error("Failed to fetch graph", err);
            message.error("无法获取图谱数据");
        }
    };

    const kbContent = (
        <Checkbox.Group
            style={{ width: '100%' }}
            value={selectedKnowledgeBases}
            onChange={(checked) => setSelectedKnowledgeBases(checked as string[])}
        >
            <Flex vertical gap={8}>
                {kbs.map(kb => (
                    <Checkbox key={kb.id} value={kb.id}>{kb.name}</Checkbox>
                ))}
                {kbs.length === 0 && <Text type="secondary" style={{ padding: 8 }}>暂无可用知识库</Text>}
            </Flex>
        </Checkbox.Group>
    );

    const historyContent = (
        <div style={{ width: 280, maxHeight: 400, overflowY: 'auto' }}>
            <List
                dataSource={conversations}
                size="small"
                renderItem={(item) => (
                    <List.Item
                        className={styles.historyItem}
                        style={{ cursor: 'pointer', background: currentConversationId === item.id ? 'var(--ant-color-primary-bg)' : 'transparent' }}
                        onClick={() => loadConversationDetails(item.id)}
                        actions={[
                            <DeleteOutlined key="delete" className={styles.deleteAction} onClick={(e) => {
                                e.stopPropagation();
                                deleteConversation(item.id);
                            }} />
                        ]}
                    >
                        <List.Item.Meta
                            title={<Text strong ellipsis={{ tooltip: item.title }}>{item.title}</Text>}
                            description={<Text type="secondary" style={{ fontSize: 12 }} ellipsis>{item.last_message_preview}</Text>}
                        />
                    </List.Item>
                )}
                locale={{ emptyText: '暂无历史记录' }}
            />
        </div>
    );

    return (
        <div className={styles.panel}>
            {/* === 面板头部 === */}
            <Flex
                align="center"
                justify="space-between"
                className={styles.panelHeader + (viewMode === 'ai' ? ' ' + styles.headerAI : '')}
            >
                <Flex align="center" gap={8}>
                    <RobotOutlined className={styles.headerIcon} />
                    <Text strong>{t('chat.title')}</Text>
                    <Tooltip title={"当前上下文: " + context.pageTitle}>
                        <Tag
                            icon={<EnvironmentOutlined />}
                            color="processing"
                            className={styles.contextTag}
                            style={{ marginLeft: 4 }}
                        >
                            {context.pageTitle}
                        </Tag>
                    </Tooltip>
                </Flex>
                <Space size={8}>
                    <Tooltip title={t('chat.history')}>
                        <Popover content={historyContent} title={t('chat.history')} trigger="click" placement="bottomRight">
                            <HistoryOutlined className={styles.headerAction} />
                        </Popover>
                    </Tooltip>
                    <Tooltip title={t('chat.new')}>
                        <PlusOutlined className={styles.headerAction} onClick={startNewChat} />
                    </Tooltip>
                    <Popover content={kbContent} title="选择知识库" trigger="click" placement="bottomRight">
                        <Tag
                            icon={<DatabaseOutlined />}
                            color={selectedKnowledgeBases.length > 0 ? "blue" : "default"}
                            className={styles.contextTag}
                            style={{ cursor: 'pointer', margin: 0 }}
                        >
                            {selectedKnowledgeBases.length > 0 ? "知识库 (" + selectedKnowledgeBases.length + ")" : '知识库'}
                        </Tag>
                    </Popover>
                    <Tooltip title="折叠">
                        <CompressOutlined className={styles.headerAction} onClick={togglePanel} />
                    </Tooltip>
                </Space>
            </Flex>

            {/* === 消息区域 === */}
            <div className={styles.messagesArea}>
                {messages.length === 0 ? (
                    <Flex vertical align="center" justify="center" className={styles.emptyState}>
                        <div className={styles.emptyIcon}>⬡</div>
                        <Text className={styles.emptyTitle}>HiveMind AI</Text>
                        <Text type="secondary" className={styles.emptyDesc}>
                            当前在「{context.pageTitle}」页面，有什么可以帮你的？
                        </Text>
                        {contextPrompts.length > 0 && (
                            <Prompts
                                items={contextPrompts}
                                onItemClick={(info) => {
                                    if (info.data.description) {
                                        handleSend(info.data.description as string);
                                    }
                                }}
                                wrap
                                className={styles.contextPrompts}
                            />
                        )}
                    </Flex>
                ) : (
                    <Bubble.List
                        items={messages.map((msg, idx) => {
                            const isUser = msg.role === 'user';
                            const isLoading = isGenerating && idx === messages.length - 1 && msg.role === 'assistant';

                            return {
                                key: msg.id || String(idx),
                                role: isUser ? 'end' : 'start',
                                avatar: isUser
                                    ? <Avatar icon={<UserOutlined />} style={{ background: '#06D6A0' }} />
                                    : <Avatar icon={<RobotOutlined />} style={{ background: '#1F2937' }} />,
                                loading: isLoading,
                                content: (
                                    <Flex vertical gap={8}>
                                        {msg.metadata?.statuses && msg.metadata.statuses.length > 0 && (
                                            <Collapse
                                                ghost
                                                size="small"
                                                expandIcon={({ isActive }) => <CaretRightOutlined rotate={isActive ? 90 : 0} style={{ color: 'var(--hm-color-primary)' }} />}
                                                className={styles.thoughtCollapse}
                                                items={[{
                                                    key: '1',
                                                    label: <span style={{ color: 'var(--hm-color-primary)', fontSize: 13, fontWeight: 500 }}>
                                                        {isLoading ? "💡 Agent 思考中..." : "💭 查看执行与检索链路"}
                                                    </span>,
                                                    children: (
                                                        <Flex vertical gap={4} style={{ marginBottom: 4 }}>
                                                            {msg.metadata.statuses.map((status: string, i: number) => {
                                                                const isGraph = status.includes('图谱');
                                                                return (
                                                                    <div
                                                                        key={i}
                                                                        className={styles.statusTag}
                                                                        style={{ cursor: isGraph ? 'pointer' : 'default', padding: '4px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)', fontSize: '12px', borderLeft: '2px solid var(--hm-color-primary)' }}
                                                                        onClick={isGraph ? fetchRealGraph : undefined}
                                                                    >
                                                                        {status} {isGraph && ' (点击查看)'}
                                                                    </div>
                                                                );
                                                            })}
                                                        </Flex>
                                                    )
                                                }]}
                                            />
                                        )}

                                        <div style={{ wordBreak: 'break-word', overflowX: 'auto', fontSize: '14px', lineHeight: '1.6' }} className={styles.markdownBody}>
                                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                                                {msg.content || (isLoading ? '...' : '')}
                                            </ReactMarkdown>
                                        </div>

                                        {msg.actions && msg.actions.length > 0 && (
                                            <Flex gap={6} wrap>
                                                {msg.actions.map((action, i) => (
                                                    <ActionButton key={i} action={action} />
                                                ))}
                                            </Flex>
                                        )}

                                        {!isUser && !isLoading && msg.metadata && (
                                            <Flex gap={12} align="center" style={{ marginTop: 4, opacity: 0.7 }}>
                                                {msg.metadata.is_cached && (
                                                    <Tooltip title="语义缓存命中: 本次回答未消耗 Token，响应极快。">
                                                        <Tag icon={<ThunderboltOutlined />} color="gold" style={{ border: 'none', background: 'rgba(255, 191, 0, 0.1)', cursor: 'default', margin: 0 }}>
                                                            CACHED
                                                        </Tag>
                                                    </Tooltip>
                                                )}
                                                {(msg.metadata.latency_ms ?? 0) > 0 && (
                                                    <Space size={4} style={{ fontSize: 11, color: '#8c8c8c' }}>
                                                        <DashboardOutlined />
                                                        <span>{((msg.metadata.latency_ms ?? 0) / 1000).toFixed(2)}s</span>
                                                    </Space>
                                                )}
                                                {(msg.metadata.total_tokens ?? 0) > 0 && (
                                                    <Space size={4} style={{ fontSize: 11, color: '#8c8c8c' }}>
                                                        <DeploymentUnitOutlined />
                                                        <span>{msg.metadata.total_tokens} tokens</span>
                                                    </Space>
                                                )}
                                                {msg.metadata.trace_data && (
                                                    <Tooltip title="查看执行追踪 (Trace)">
                                                        <Tag
                                                            icon={<BugOutlined />}
                                                            color="error"
                                                            style={{ cursor: 'pointer', margin: 0, padding: '0 8px', borderRadius: 4, background: 'rgba(255, 77, 79, 0.1)', border: '1px solid rgba(255, 77, 79, 0.2)', fontSize: 11 }}
                                                            onClick={() => {
                                                                try {
                                                                    if (msg.metadata?.trace_data) {
                                                                        setCurrentTrace(JSON.parse(msg.metadata.trace_data));
                                                                        setIsTraceModalOpen(true);
                                                                    }
                                                                } catch (e) {
                                                                    message.error("解析追踪数据失败");
                                                                }
                                                            }}
                                                        >
                                                            TRACE
                                                        </Tag>
                                                    </Tooltip>
                                                )}
                                            </Flex>
                                        )}

                                        {!isUser && !isLoading && (
                                            <Flex gap={8} style={{ marginTop: 2 }}>
                                                <Tooltip title={t('chat.feedback.good')}>
                                                    {msg.rating === 1 ? (
                                                        <LikeFilled style={{ color: '#1890ff', cursor: 'pointer' }} onClick={() => handleFeedback(msg.id!, 0)} />
                                                    ) : (
                                                        <LikeOutlined
                                                            style={{ color: '#8c8c8c', cursor: 'pointer' }}
                                                            onClick={() => handleFeedback(msg.id!, 1)}
                                                        />
                                                    )}
                                                </Tooltip>
                                                <Tooltip title={t('chat.feedback.bad')}>
                                                    {msg.rating === -1 ? (
                                                        <DislikeFilled style={{ color: '#ff4d4f', cursor: 'pointer' }} onClick={() => handleFeedback(msg.id!, 0)} />
                                                    ) : (
                                                        <DislikeOutlined
                                                            style={{ color: '#8c8c8c', cursor: 'pointer' }}
                                                            onClick={() => handleFeedback(msg.id!, -1)}
                                                        />
                                                    )}
                                                </Tooltip>
                                            </Flex>
                                        )}
                                    </Flex>
                                ),
                            } as any;
                        })}
                        className={styles.bubbleList}
                    />
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className={styles.inputArea}>
                {context.availableActions.length > 0 && (
                    <div className={styles.promptsContainer}>
                        <Prompts
                            items={context.availableActions.map(action => ({
                                key: action.label,
                                label: (
                                    <Space size={4}>
                                        {action.variant === 'primary' && <ThunderboltOutlined style={{ color: '#faad14' }} />}
                                        <span>{action.label}</span>
                                    </Space>
                                ),
                                description: action.type === 'navigate' ? "前往 " + action.label : action.label,
                                action: action
                            }))}
                            onItemClick={(info) => {
                                const action = (info.data as any).action;
                                handlePromptClick(action);
                            }}
                            className={styles.prompts}
                        />
                    </div>
                )}
                <Sender
                    value={inputValue}
                    onChange={setInputValue}
                    onSubmit={handleSend}
                    loading={isGenerating}
                    placeholder={t('chat.placeholder')}
                    className={styles.sender}
                />
            </div>

            {/* 图谱可视化 Modal */}
            <Modal
                title="记忆图谱 (Tier 2)"
                open={isGraphModalOpen}
                onCancel={() => setIsGraphModalOpen(false)}
                footer={null}
                width={800}
                styles={{ body: { height: 600, padding: 0, background: '#0A0E1A' } }}
                centered
                destroyOnHidden
            >
                {graphData && <GraphVisualizer data={graphData} width={800} height={600} />}
            </Modal>

            {/* Trace 可观察性 Modal */}
            <Modal
                title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><BugOutlined style={{ color: 'var(--ant-color-primary)' }} /> 执行追踪 (Custom Tracing)</span>}
                open={isTraceModalOpen}
                onCancel={() => setIsTraceModalOpen(false)}
                footer={null}
                width={650}
                centered
                styles={{ body: { padding: '24px 32px' } }}
            >
                <div style={{ maxHeight: 600, overflowY: 'auto', paddingRight: 8 }}>
                    <Timeline
                        mode="left"
                        items={(currentTrace || []).map((step) => ({
                            color: step.status === 'success' ? '#52c41a' : step.status === 'error' ? '#ff4d4f' : '#1890ff',
                            dot: step.status === 'success' ? <CheckCircleOutlined /> : step.status === 'error' ? <ExclamationCircleOutlined /> : <ClockCircleOutlined />,
                            children: (
                                <div style={{ marginBottom: 16 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                        <Text strong style={{ fontSize: 14 }}>{step.name}</Text>
                                        <Tag color="default" style={{ border: 'none', background: 'rgba(0,0,0,0.04)', fontSize: 11 }}>
                                            {step.duration_ms.toFixed(1)}ms
                                        </Tag>
                                    </div>
                                    <div style={{ marginBottom: 8 }}>
                                        <Tag color="blue" style={{ fontSize: 10, borderRadius: 2 }}>{step.type.toUpperCase()}</Tag>
                                        {step.status === 'error' && <Tag color="error" style={{ fontSize: 10 }}>FAILED</Tag>}</div >

                                    {step.input && (
                                        <div style={{ background: 'rgba(0,0,0,0.02)', padding: '8px 12px', borderRadius: 6, marginBottom: 8 }}>
                                            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 2 }}>INPUT:</Text>
                                            <div style={{ fontSize: 12, fontFamily: 'monospace', wordBreak: 'break-all', color: '#595959' }}>
                                                {typeof step.input === 'string' ? step.input : JSON.stringify(step.input)}
                                            </div>
                                        </div>
                                    )}

                                    {step.metadata?.logs && (
                                        <Collapse ghost size="small" style={{ marginBottom: 8, background: '#f6ffed', borderRadius: 4, border: '1px solid #d9f7be' }}>
                                            <Collapse.Panel header={<span style={{ fontSize: 12, color: '#389e0d' }}>查看检索明细 ({step.metadata.logs.length} 条)</span>} key="1">
                                                <List
                                                    size="small"
                                                    dataSource={step.metadata.logs}
                                                    renderItem={(log: string) => (
                                                        <List.Item style={{ padding: '4px 0', border: 'none' }}>
                                                            <Text code style={{ fontSize: 11, width: '100%' }}>{log}</Text>
                                                        </List.Item>
                                                    )}
                                                />
                                            </Collapse.Panel>
                                        </Collapse>
                                    )}

                                    {step.metadata?.docs && step.metadata.docs.length > 0 && (
                                        <Collapse ghost size="small" style={{ marginBottom: 8, background: '#f0f5ff', borderRadius: 4, border: '1px solid #adc6ff' }}>
                                            <Collapse.Panel header={<span style={{ fontSize: 12, color: '#003a8c' }}><FileSearchOutlined /> 查看知识分块 ({step.metadata.docs.length} 个)</span>} key="2">
                                                <List
                                                    size="small"
                                                    dataSource={step.metadata.docs}
                                                    renderItem={(doc: any, i: number) => (
                                                        <div key={i} style={{ padding: '8px', borderBottom: i < step.metadata.docs.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                                                            <Flex justify="space-between" align="center" style={{ marginBottom: 4 }}>
                                                                <Tag color="blue" style={{ fontSize: 10, borderRadius: 2 }}>分块 {i + 1}</Tag>
                                                                <Text type="secondary" style={{ fontSize: 10 }}>匹配度: {(doc.score || 0).toFixed(4)}</Text>
                                                            </Flex>
                                                            <Text
                                                                style={{
                                                                    fontSize: 11,
                                                                    color: 'var(--ant-color-primary)',
                                                                    display: 'block',
                                                                    marginBottom: 4,
                                                                    cursor: 'pointer',
                                                                    textDecoration: 'underline'
                                                                }}
                                                                onClick={() => {
                                                                    const kbId = doc.metadata?.kb_id;
                                                                    const docId = doc.metadata?.doc_id;
                                                                    if (kbId) {
                                                                        navigate('/knowledge?kbId=' + kbId + (docId ? '&docId=' + docId : ''));
                                                                        setIsTraceModalOpen(false);
                                                                    } else {
                                                                        message.warning("无法定位归属知识库");
                                                                    }
                                                                }}
                                                            >
                                                                来源: {doc.metadata?.file_name || '未知文件'} (第 {doc.metadata?.page || '?'} 页)
                                                            </Text>
                                                            <div style={{
                                                                fontSize: 12,
                                                                background: '#fff',
                                                                padding: '8px',
                                                                borderRadius: '4px',
                                                                border: '1px solid #f0f0f0',
                                                                maxHeight: '120px',
                                                                overflowY: 'auto',
                                                                whiteSpace: 'pre-wrap',
                                                                color: '#262626',
                                                                lineHeight: '1.5'
                                                            }}>
                                                                {doc.page_content}
                                                            </div>
                                                        </div>
                                                    )}
                                                />
                                            </Collapse.Panel>
                                        </Collapse>
                                    )}

                                    {step.output && step.status !== 'error' && (
                                        <div style={{ background: 'rgba(82, 196, 26, 0.04)', padding: '8px 12px', borderRadius: 6, border: '1px solid rgba(82, 196, 26, 0.1)' }}>
                                            <Text type="secondary" style={{ fontSize: 11, display: 'block', color: '#389e0d', marginBottom: 2 }}>OUTPUT:</Text>
                                            <div style={{ fontSize: 12, color: '#2b2b2b' }}>
                                                {typeof step.output === 'string' ? step.output : JSON.stringify(step.output)}
                                            </div>
                                        </div>
                                    )}

                                    {step.status === 'error' && step.output && (
                                        <div style={{ background: 'rgba(255, 77, 79, 0.04)', padding: '8px 12px', borderRadius: 6, border: '1px solid rgba(255, 77, 79, 0.1)' }}>
                                            <Text type="danger" style={{ fontSize: 11, display: 'block', marginBottom: 2 }}>ERROR:</Text>
                                            <div style={{ fontSize: 12, color: '#cf1322', fontWeight: 500 }}>
                                                {step.output}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )
                        }))}
                    />
                </div>
            </Modal>
        </div>
    );
};
