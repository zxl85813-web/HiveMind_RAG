/**
 * ChatPanel — AI 对话面板 (永驻右侧)。
 *
 * 这是 AI-First 架构的核心组件:
 *   - 始终显示在布局右侧 (可折叠)
 *   - 感知当前页面上下文
 *   - AI 回答中可嵌入 ActionButton
 *   - 上方显示上下文指示器
 *
 * @module components/chat
 * @see docs/design/ai-first-frontend.md
 */

import React, { useState, useRef, useEffect } from 'react';
import { Flex, Typography, Tooltip, Tag, Space, Avatar, Popover, Checkbox, message, List, Modal } from 'antd';
import { Bubble, Sender, Prompts } from '@ant-design/x';
import {
    RobotOutlined,
    UserOutlined,
    CompressOutlined,
    ClearOutlined,
    EnvironmentOutlined,
    LikeOutlined,
    DislikeOutlined,
    LikeFilled,
    DislikeFilled,
    DatabaseOutlined,
    HistoryOutlined,
    PlusOutlined,
    DeleteOutlined
} from '@ant-design/icons';

import { useChatStore } from '../../stores/chatStore';
import { ActionButton } from './ActionButton';
import { chatApi } from '../../services/chatApi';
import { knowledgeApi } from '../../services/knowledgeApi';
import { memoryApi } from '../../services/memoryApi';
import { GraphVisualizer } from '../knowledge/GraphVisualizer';
import type { KnowledgeBase } from '../../types';
import styles from './ChatPanel.module.css';

const { Text } = Typography;

export const ChatPanel: React.FC = () => {
    const {
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
        setCurrentConversation
    } = useChatStore();

    const [inputValue, setInputValue] = useState('');
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [isGraphModalOpen, setIsGraphModalOpen] = useState(false);
    const [graphData, setGraphData] = useState<{ nodes: any[], links: any[] } | null>(null);
    const [radarTags, setRadarTags] = useState<string[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Fetch KBs
    // Initial Load
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

    /** 发送消息 */
    const handleSend = async (value: string) => {
        if (!value.trim()) return;
        setRadarTags([]); // Reset tags for new query

        const userMsgId = `user-${Date.now()}`;
        // 1. 添加用户消息
        addMessage({
            id: userMsgId,
            role: 'user',
            content: value,
            created_at: new Date().toISOString(),
            metadata: { context_page: context.currentPage },
        });
        setInputValue('');
        setGenerating(true);

        // 2. 预先添加一个空的 AI 消息 (用于流式更新)
        const aiMsgId = `ai-${Date.now()}`;
        addMessage({
            id: aiMsgId,
            role: 'assistant',
            content: '', // 初始为空
            created_at: new Date().toISOString(),
            // actions: [], // 后续根据 content 解析
        });

        // 3. 发起流式请求
        // 累积内容缓冲区
        let fullContent = '';

        await chatApi.streamChat({
            message: value,
            conversationId: currentConversationId,
            knowledgeBaseIds: useChatStore.getState().selectedKnowledgeBases,
            onDelta: (delta) => {
                fullContent += delta;
                useChatStore.getState().updateLastMessage(fullContent);
            },
            onStatus: (status) => {
                useChatStore.getState().appendStatusToLastMessage(status);
                const match = status.match(/Tags: \[(.*?)\]/);
                if (match && match[1]) {
                    const tags = match[1].split(',').map(t => t.trim());
                    setRadarTags(prev => [...new Set([...prev, ...tags])]);
                }
            },
            onSessionCreated: (id) => {
                setCurrentConversation(id);
                loadConversations(); // Refresh list
            },
            onFinish: () => {
                setGenerating(false);
                loadConversations(); // Update previews
            },
            onError: (err) => {
                console.error('Chat error:', err);
                fullContent += '\n[系统错误: 无法连接到 AI 服务]';
                useChatStore.getState().updateLastMessage(fullContent);
                setGenerating(false);
            }
        });
    };

    /** 将上下文快捷操作转为 Prompts 项 */
    const contextPrompts = context.availableActions.slice(0, 3).map((action) => ({
        key: action.target,
        label: action.label,
        description: `${action.type === 'navigate' ? '跳转到' : ''}${action.label}`,
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
            <Flex align="center" justify="space-between" className={styles.panelHeader}>
                <Flex align="center" gap={8}>
                    <RobotOutlined className={styles.headerIcon} />
                    <Text strong>AI 助手</Text>
                </Flex>
                <Space size={4}>
                    <Tooltip title="历史记录">
                        <Popover content={historyContent} title="历史对话" trigger="click" placement="bottomRight">
                            <HistoryOutlined className={styles.headerAction} />
                        </Popover>
                    </Tooltip>

                    <Tooltip title="开启新对话">
                        <PlusOutlined className={styles.headerAction} onClick={startNewChat} />
                    </Tooltip>

                    {/* 知识库选择器 */}
                    <Popover content={kbContent} title="选择知识库" trigger="click" placement="bottomRight">
                        <Tag
                            icon={<DatabaseOutlined />}
                            color={selectedKnowledgeBases.length > 0 ? "blue" : "default"}
                            className={styles.contextTag}
                            style={{ cursor: 'pointer' }}
                        >
                            {selectedKnowledgeBases.length > 0 ? `知识库 (${selectedKnowledgeBases.length})` : '知识库'}
                        </Tag>
                    </Popover>

                    {/* 上下文指示 */}
                    <Tooltip title={`当前上下文: ${context.pageTitle}`}>
                        <Tag
                            icon={<EnvironmentOutlined />}
                            color="processing"
                            className={styles.contextTag}
                        >
                            {context.pageTitle}
                        </Tag>
                    </Tooltip>

                    <Tooltip title="折叠">
                        <CompressOutlined className={styles.headerAction} onClick={togglePanel} />
                    </Tooltip>
                </Space>
            </Flex>

            {/* === 消息区域 === */}
            <div className={styles.messagesArea}>
                {messages.length === 0 ? (
                    /* 空状态: 显示上下文快捷操作 */
                    <Flex vertical align="center" justify="center" className={styles.emptyState}>
                        <div className={styles.emptyIcon}>⬡</div>
                        <Text className={styles.emptyTitle}>HiveMind AI</Text>
                        <Text type="secondary" className={styles.emptyDesc}>
                            当前在「{context.pageTitle}」页面，有什么可以帮你的？
                        </Text>
                        {contextPrompts.length > 0 && (
                            <Prompts
                                items={contextPrompts}
                                onItemClick={(info) => handleSend(info.data.description as string)}
                                wrap
                                className={styles.contextPrompts}
                            />
                        )}
                    </Flex>
                ) : (
                    /* 消息列表 */
                    <Bubble.List
                        items={messages.map((msg, idx) => {
                            const isUser = msg.role === 'user';
                            const isLoading = isGenerating && idx === messages.length - 1 && msg.role === 'assistant';

                            // 构造符合 Ant Design X Bubble.List 的 item 对象
                            return {
                                key: msg.id || String(idx),
                                role: isUser ? 'end' : 'start',
                                content: msg.content,
                                avatar: isUser
                                    ? <Avatar icon={<UserOutlined />} style={{ background: '#06D6A0' }} />
                                    : <Avatar icon={<RobotOutlined />} style={{ background: '#1F2937' }} />,
                                loading: isLoading,
                                messageRender: () => (
                                    <Flex vertical gap={8}>
                                        {/* Statuses (Memory/Graph Nodes) */}
                                        {msg.metadata?.statuses && msg.metadata.statuses.length > 0 && (
                                            <Flex vertical gap={4} style={{ marginBottom: 4 }}>
                                                {msg.metadata.statuses.map((status, i) => {
                                                    const isGraph = status.includes('图谱');
                                                    return (
                                                        <div
                                                            key={i}
                                                            className={styles.statusTag}
                                                            style={{ cursor: isGraph ? 'pointer' : 'default' }}
                                                            onClick={isGraph ? fetchRealGraph : undefined}
                                                        >
                                                            {status} {isGraph && ' (点击查看)'}
                                                        </div>
                                                    );
                                                })}
                                            </Flex>
                                        )}

                                        <div style={{ wordBreak: 'break-word' }}>{msg.content}</div>

                                        {/* Actions */}
                                        {msg.actions && msg.actions.length > 0 && (
                                            <Flex gap={6} wrap>
                                                {msg.actions.map((action, i) => (
                                                    <ActionButton key={i} action={action} />
                                                ))}
                                            </Flex>
                                        )}

                                        {/* Feedback Buttons (Only for Assistant & Not Generating) */}
                                        {!isUser && !isLoading && (
                                            <Flex gap={8} style={{ marginTop: 4 }}>
                                                <Tooltip title="有帮助">
                                                    {msg.rating === 1 ? (
                                                        <LikeFilled style={{ color: '#1890ff', cursor: 'pointer' }} />
                                                    ) : (
                                                        <LikeOutlined
                                                            style={{ color: '#8c8c8c', cursor: 'pointer' }}
                                                            onClick={() => handleFeedback(msg.id, 1)}
                                                        />
                                                    )}
                                                </Tooltip>

                                                <Tooltip title="无帮助">
                                                    {msg.rating === -1 ? (
                                                        <DislikeFilled style={{ color: '#ff4d4f', cursor: 'pointer' }} />
                                                    ) : (
                                                        <DislikeOutlined
                                                            style={{ color: '#8c8c8c', cursor: 'pointer' }}
                                                            onClick={() => handleFeedback(msg.id, -1)}
                                                        />
                                                    )}
                                                </Tooltip>
                                            </Flex>
                                        )}
                                    </Flex>
                                ),
                            } as React.ComponentProps<typeof Bubble.List>['items'][number];
                        })}
                        className={styles.bubbleList}
                    />
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* === 输入区域 === */}
            <div className={styles.inputArea}>
                <Sender
                    value={inputValue}
                    onChange={setInputValue}
                    onSubmit={handleSend}
                    loading={isGenerating}
                    placeholder={`在「${context.pageTitle}」问我任何问题...`}
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
                bodyStyle={{ height: 600, padding: 0, background: '#0A0E1A' }}
                centered
                destroyOnClose
            >
                {graphData && <GraphVisualizer data={graphData} width={800} height={600} />}
            </Modal>
        </div>
    );
};

// ==========================================
//  Mock Helpers (开发阶段)
// ==========================================

/* unused
function generateMockReply(input: string, pageName: string): string {
    if (input.includes('知识库') || input.includes('创建')) {
        return '好的，我帮你准备知识库创建流程。你可以点击下方按钮直接前往，或者告诉我你想创建什么类型的知识库。';
    }
    if (input.includes('Agent') || input.includes('状态')) {
        return '当前所有 Agent 处于空闲状态。Supervisor 待命中，随时可以处理新任务。';
    }
    if (input.includes('动态') || input.includes('开源')) {
        return '让我帮你查看最新的技术动态。目前外部学习引擎还未启动，你可以先添加订阅源。';
    }
    return `我收到了你在「${pageName}」页面的问题。实际实现中，我会根据你当前的页面上下文，调用对应的 Agent 来回答。`;
}

function generateMockActions(input: string, _currentPage: string): AIAction[] {
    if (input.includes('知识库') || input.includes('创建')) {
        return [
            { type: 'navigate', label: '前往知识库', target: '/knowledge', icon: 'DatabaseOutlined', variant: 'primary' },
        ];
    }
    if (input.includes('Agent') || input.includes('状态')) {
        return [
            { type: 'navigate', label: '查看监控面板', target: '/agents', icon: 'ClusterOutlined', variant: 'primary' },
        ];
    }
    if (input.includes('动态') || input.includes('开源') || input.includes('项目')) {
        return [
            { type: 'navigate', label: '查看技术动态', target: '/learning', icon: 'BulbOutlined', variant: 'primary' },
        ];
    }
    if (input.includes('设置') || input.includes('模型') || input.includes('配置')) {
        return [
            { type: 'navigate', label: '打开设置', target: '/settings', icon: 'SettingOutlined' },
        ];
    }
    return [];
}
*/
