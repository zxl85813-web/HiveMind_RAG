import React, { useMemo, useRef, useState } from 'react';
import { Flex, Avatar, Typography, Tag, Spin, Space, theme } from 'antd';
import { Bubble, Sender, Welcome, Prompts } from '@ant-design/x';
import {
    RobotOutlined,
    UserOutlined,
    BulbOutlined,
    SearchOutlined,
    FileTextOutlined,
    CodeOutlined,
    ThunderboltOutlined,
    LoadingOutlined,
} from '@ant-design/icons';
import { ActionButton } from '../components/chat/ActionButton';
import { chatApi } from '../services/chatApi';
import styles from './ChatPage.module.css';

const { Text } = Typography;

export const ChatPage: React.FC = () => {
    const { token } = theme.useToken();
    const promptItems = useMemo(() => [
        {
            key: 'rag',
            icon: <SearchOutlined style={{ color: token.colorPrimary }} />,
            label: '知识库检索',
            description: '从知识库中查找相关信息',
        },
        {
            key: 'summary',
            icon: <FileTextOutlined style={{ color: token.colorInfo }} />,
            label: '文档摘要',
            description: '总结文档的核心内容',
        },
        {
            key: 'code',
            icon: <CodeOutlined style={{ color: token.colorWarning }} />,
            label: '代码生成',
            description: '根据需求生成代码',
        },
        {
            key: 'analysis',
            icon: <BulbOutlined style={{ color: token.colorError }} />,
            label: '数据分析',
            description: '分析和查询数据',
        },
    ], [token.colorError, token.colorInfo, token.colorPrimary, token.colorWarning]);
    const [messages, setMessages] = useState<Array<{
        role: 'user' | 'assistant';
        content: string;
        status?: string;
        actions?: any[];
    }>>([]);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
    const [agentStatus, setAgentStatus] = useState<string | null>(null);

    const abortControllerRef = useRef<AbortController | null>(null);

    /** 发送消息 */
    const handleSend = async (value: string) => {
        if (!value.trim()) return;

        // 1. Add user message
        setMessages((prev) => [...prev, { role: 'user', content: value }]);
        setInputValue('');
        setLoading(true);
        setAgentStatus('🚀 准备启动 Swarm 编排器...');

        // 2. Prepare assistant message placeholder
        setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

        const controller = new AbortController();
        abortControllerRef.current = controller;

        let fullContent = '';

        // 3. Start SSE
        await chatApi.streamChat({
            message: value,
            conversationId: currentConversationId,
            onDelta: (delta) => {
                fullContent += delta;
                setMessages((prev) => {
                    const newMsgs = [...prev];
                    const lastMsg = newMsgs[newMsgs.length - 1];
                    if (lastMsg && lastMsg.role === 'assistant') {
                        lastMsg.content = fullContent;
                    }
                    return newMsgs;
                });
            },
            onStatus: (status) => {
                setAgentStatus(status);
            },
            onInsight: (data) => {
                setMessages((prev) => {
                    const newMsgs = [...prev];
                    const lastMsg = newMsgs[newMsgs.length - 1];
                    if (lastMsg && lastMsg.role === 'assistant') {
                        // @ts-expect-error: actions property might not be in the base message type
                        lastMsg.actions = data.actions;
                    }
                    return newMsgs;
                });
            },
            onSessionCreated: (id) => {
                setCurrentConversationId(id);
            },
            onFinish: () => {
                setLoading(false);
                setAgentStatus(null);
            },
            onError: (err) => {
                console.error('Chat error:', err);
                setLoading(false);
                setAgentStatus('❌ 服务连接异常，请重试');
            },
            controller
        });
    };

    /** 渲染状态标签 */
    const renderStatus = () => {
        if (!agentStatus) return null;
        return (
            <div className={styles.statusIndicator}>
                <Space>
                    <Spin indicator={<LoadingOutlined style={{ fontSize: 14, color: token.colorPrimary }} spin />} />
                    <Text type="secondary" className={styles.statusText}>
                        {agentStatus}
                    </Text>
                    <Tag color="cyan" variant="filled" icon={<ThunderboltOutlined />}>HiveMind Swarm</Tag>
                </Space>
            </div>
        );
    };

    /** 空状态 — 欢迎页 */
    const renderWelcome = () => (
        <Flex vertical align="center" justify="center" className={styles.welcomeContainer}>
            <Welcome
                icon={<RobotOutlined style={{ fontSize: 40, color: token.colorPrimary }} />}
                title="HiveMind AI 助手"
                description="基于 Agent 蜂巢架构的智能 RAG 平台，支持知识库检索、数据分析、代码生成等能力。"
                className={styles.welcome}
            />
            <Prompts
                items={promptItems}
                onItemClick={(info) => handleSend(info.data.description as string)}
                wrap
                className={styles.prompts}
            />
        </Flex>
    );

    /** 消息列表 */
    const renderMessages = () => {
        return (
            <Flex vertical className={styles.messageList}>
                <Bubble.List
                    items={messages.map((msg, idx) => ({
                        key: String(idx),
                        role: msg.role === 'user' ? 'end' : 'start',
                        content: msg.content || (loading && idx === messages.length - 1 ? '...' : ''),
                        avatar: msg.role === 'user'
                            ? <Avatar icon={<UserOutlined />} style={{ background: token.colorPrimary }} />
                            : <Avatar icon={<RobotOutlined />} style={{ background: token.colorBgElevated, border: 'var(--hm-border-brand)' }} />,
                        footer: (
                            <Space direction="vertical" style={{ width: '100%', marginTop: 8 }}>
                                {idx === messages.length - 1 && msg.role === 'assistant' && renderStatus()}
                                {msg.actions && msg.actions.length > 0 && (
                                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                                        {msg.actions.map((action, actionIdx) => (
                                            <ActionButton key={actionIdx} action={action} />
                                        ))}
                                    </div>
                                )}
                            </Space>
                        ),
                    }))}
                    className={styles.bubbleList}
                />
            </Flex>
        );
    };

    return (
        <Flex vertical className={styles.container}>
            {/* 消息区域 */}
            <div className={styles.messagesArea}>
                {messages.length === 0 ? renderWelcome() : renderMessages()}
            </div>

            {/* 输入区域 */}
            <div className={styles.senderArea}>
                <Sender
                    value={inputValue}
                    onChange={setInputValue}
                    onSubmit={handleSend}
                    loading={loading}
                    placeholder="输入你的问题... (支持知识库检索、数据分析等)"
                    className={styles.sender}
                />
            </div>
        </Flex>
    );
};
