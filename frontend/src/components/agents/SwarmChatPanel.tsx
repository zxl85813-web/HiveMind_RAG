import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Space, Typography, Badge, Tooltip, message as antdMessage } from 'antd';
import { 
    SendOutlined, 
    RobotOutlined, 
    LoadingOutlined,
    HistoryOutlined
} from '@ant-design/icons';
import styles from './SwarmChatPanel.module.css';
import { agentApi } from '../../services/agentApi';
import { ChatBubble } from './ChatBubble';
import type { ChatMessage } from './ChatBubble';

export const SwarmChatPanel: React.FC = () => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [currentNode, setCurrentNode] = useState<string | null>(null);
    
    const scrollRef = useRef<HTMLDivElement>(null);
    const conversationIdRef = useRef<string>(Math.random().toString(36).substring(7));

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, currentNode]);

    const handleSend = async () => {
        if (!inputValue.trim() || isStreaming) return;

        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue,
        };

        setMessages(prev => [...prev, userMsg]);
        setInputValue('');
        setIsStreaming(true);
        setCurrentNode('supervisor');

        const swarmMsgId = (Date.now() + 1).toString();
        let currentContent = '';
        const currentThoughts: string[] = [];

        try {
            const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
            const url = `${apiBase}${agentApi.SWARM_CHAT_URL}`;

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: inputValue,
                    conversation_id: conversationIdRef.current,
                    kb_ids: []
                })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) throw new Error('No reader available');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.event === 'node_start') {
                            setCurrentNode(data.node);
                        } else if (data.event === 'thought') {
                            currentThoughts.push(data.content);
                            setMessages(prev => {
                                const last = prev[prev.length - 1];
                                if (last?.role === 'swarm' && last.id === swarmMsgId) {
                                    return [...prev.slice(0, -1), { ...last, thoughts: [...currentThoughts] }];
                                }
                                return [...prev, { id: swarmMsgId, role: 'swarm', content: '', thoughts: [...currentThoughts] }];
                            });
                        } else if (data.event === 'delta') {
                            currentContent += data.content;
                            setMessages(prev => {
                                const last = prev[prev.length - 1];
                                if (last?.role === 'swarm' && last.id === swarmMsgId) {
                                    return [...prev.slice(0, -1), { ...last, content: currentContent }];
                                }
                                return [...prev, { id: swarmMsgId, role: 'swarm', content: currentContent, thoughts: [...currentThoughts] }];
                            });
                        } else if (data.event === 'node_end') {
                            setCurrentNode(null);
                        } else if (data.event === 'error') {
                            antdMessage.error(data.message);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('SSE Error:', error);
            antdMessage.error('无法连接到 Agent 集群，请检查后端状态。');
        } finally {
            setIsStreaming(false);
            setCurrentNode(null);
        }
    };

    return (
        <div className={styles.swarmChatPanel}>
            <div className={styles.chatMessages} ref={scrollRef}>
                {messages.length === 0 && (
                    <div style={{ textAlign: 'center', marginTop: '15%', padding: '0 40px' }}>
                        <RobotOutlined style={{ fontSize: 48, color: 'var(--hm-color-brand-dim)', marginBottom: 16 }} />
                        <Typography.Text strong style={{ display: 'block', fontSize: 18 }}>Agent Swarm 实时监控台</Typography.Text>
                        <Typography.Text type="secondary">发送消息以触发 Agent 协作，下方将实时展示节点的思考与执行路径。</Typography.Text>
                    </div>
                )}
                
                {messages.map((msg) => (
                    <ChatBubble key={msg.id} message={msg} />
                ))}
                
                {isStreaming && currentNode && (
                    <div style={{ alignSelf: 'flex-start', background: 'transparent', padding: '0 16px' }}>
                        <Space className={styles.typingIndicator}>
                            <Badge status="processing" text={<Typography.Text type="secondary" style={{fontSize: '12px'}}>{`Agent Node [${currentNode}] is thinking...`}</Typography.Text>} />
                            <div className={styles.dot}></div>
                            <div className={styles.dot}></div>
                            <div className={styles.dot}></div>
                        </Space>
                    </div>
                )}
            </div>

            <div className={styles.chatInputArea}>
                <Input
                    placeholder="输入指令 (例如：分析系统架构并创建对应知识库)"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onPressEnter={handleSend}
                    disabled={isStreaming}
                    prefix={<HistoryOutlined style={{ color: 'var(--hm-color-text-quaternary)' }} />}
                    suffix={
                        <Tooltip title="快捷指令: /analyze /search">
                            <RobotOutlined style={{ color: 'var(--hm-color-text-quaternary)' }} />
                        </Tooltip>
                    }
                />
                <Button 
                    type="primary" 
                    icon={isStreaming ? <LoadingOutlined /> : <SendOutlined />} 
                    onClick={handleSend}
                    disabled={isStreaming || !inputValue.trim()}
                />
            </div>
        </div>
    );
};
