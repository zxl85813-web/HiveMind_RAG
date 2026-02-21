/**
 * ChatPage — 主对话页面。
 *
 * 使用 Ant Design X 的 Bubble, Sender 等组件构建 AI 对话界面。
 * 品牌色: #06D6A0 (青绿)
 *
 * @module pages
 * @see REGISTRY.md > 前端 > 页面 > ChatPage
 */

import React, { useState } from 'react';
import { Flex, Avatar } from 'antd';
import { Bubble, Sender, Welcome, Prompts } from '@ant-design/x';
import {
    RobotOutlined,
    UserOutlined,
    BulbOutlined,
    SearchOutlined,
    FileTextOutlined,
    CodeOutlined,
} from '@ant-design/icons';
import styles from './ChatPage.module.css';

/** 预设快捷提示 */
const promptItems = [
    {
        key: 'rag',
        icon: <SearchOutlined style={{ color: '#06D6A0' }} />,
        label: '知识库检索',
        description: '从知识库中查找相关信息',
    },
    {
        key: 'summary',
        icon: <FileTextOutlined style={{ color: '#118AB2' }} />,
        label: '文档摘要',
        description: '总结文档的核心内容',
    },
    {
        key: 'code',
        icon: <CodeOutlined style={{ color: '#FFD166' }} />,
        label: '代码生成',
        description: '根据需求生成代码',
    },
    {
        key: 'analysis',
        icon: <BulbOutlined style={{ color: '#EF476F' }} />,
        label: '数据分析',
        description: '分析和查询数据',
    },
];

export const ChatPage: React.FC = () => {
    const [messages, setMessages] = useState<Array<{
        role: 'user' | 'assistant';
        content: string;
    }>>([]);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);

    /** 发送消息 */
    const handleSend = async (value: string) => {
        if (!value.trim()) return;

        setMessages((prev) => [...prev, { role: 'user', content: value }]);
        setInputValue('');
        setLoading(true);

        // TODO: 实际调用后端 SSE 流式接口
        setTimeout(() => {
            setMessages((prev) => [
                ...prev,
                {
                    role: 'assistant',
                    content: `收到你的问题: "${value}"\n\n这是一个模拟回答。实际实现中，这里会通过 SSE 流式连接接收 Agent Swarm 的回答。`,
                },
            ]);
            setLoading(false);
        }, 1000);
    };

    /** 空状态 — 欢迎页 */
    const renderWelcome = () => (
        <Flex vertical align="center" justify="center" className={styles.welcomeContainer}>
            <Welcome
                icon={<RobotOutlined style={{ fontSize: 40, color: '#06D6A0' }} />}
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
    const renderMessages = () => (
        <Flex vertical className={styles.messageList}>
            <Bubble.List
                items={messages.map((msg, idx) => ({
                    key: String(idx),
                    role: msg.role === 'user' ? 'end' : 'start',
                    content: msg.content,
                    avatar: msg.role === 'user'
                        ? <Avatar icon={<UserOutlined />} style={{ background: '#06D6A0' }} />
                        : <Avatar icon={<RobotOutlined />} style={{ background: '#1F2937', border: '1px solid rgba(6,214,160,0.25)' }} />,
                    loading: loading && idx === messages.length - 1 && msg.role === 'assistant',
                }))}
                className={styles.bubbleList}
            />
        </Flex>
    );

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
