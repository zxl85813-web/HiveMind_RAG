import React, { useState } from 'react';
import { Typography, Space, Avatar, Button, Tooltip } from 'antd';
import { 
    RobotOutlined, 
    BulbOutlined, 
    CopyOutlined, 
    CheckOutlined,
    PlayCircleOutlined 
} from '@ant-design/icons';
import styles from './ChatBubble.module.css';

const { Text, Paragraph } = Typography;

export interface ChatMessage {
    id: string;
    role: 'user' | 'swarm';
    content: string;
    thoughts?: string[];
}

interface ChatBubbleProps {
    message: ChatMessage;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        if (!message.content) return;
        
        // Clean ACTION strings before copying if necessary, 
        // but for now we copy the raw text as it's the simplest
        const textToCopy = message.content.replace(/\[ACTION: (.*?)\]/, '');
        
        navigator.clipboard.writeText(textToCopy);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const renderAction = (content: string) => {
        const actionMatch = content.match(/\[ACTION: (.*?)\]/);
        if (actionMatch) {
            try {
                const action = JSON.parse(actionMatch[1]);
                const cleanContent = content.replace(/\[ACTION: (.*?)\]/, '');
                
                return (
                    <div className={styles.actionContainer}>
                        <Paragraph style={{ marginBottom: 8, color: 'inherit' }}>{cleanContent}</Paragraph>
                        <Button 
                            type={action.variant === 'primary' ? 'primary' : 'default'}
                            icon={<PlayCircleOutlined />}
                            shape="round"
                            size="small"
                            onClick={() => window.location.href = action.target}
                        >
                            {action.label}
                        </Button>
                    </div>
                );
            } catch (e) {
                return <Paragraph style={{ color: 'inherit' }}>{content}</Paragraph>;
            }
        }
        return <Paragraph style={{ color: 'inherit' }}>{content}</Paragraph>;
    };

    return (
        <div className={`${styles.chatBubble} ${message.role === 'user' ? styles.userMessage : styles.swarmMessage}`}>
            {message.role === 'swarm' && (
                <div style={{ marginBottom: 8 }}>
                    <Space>
                        <Avatar size="small" icon={<RobotOutlined />} style={{ backgroundColor: 'var(--hm-color-brand)' }} />
                        <Text strong style={{ color: 'inherit' }}>HiveMind Swarm</Text>
                    </Space>
                </div>
            )}
            
            {message.thoughts?.map((thought, idx) => (
                <div key={idx} className={styles.thoughtBubble}>
                    <BulbOutlined />
                    <span>{thought}</span>
                </div>
            ))}
            
            <div className={styles.contentArea}>
                {renderAction(message.content)}
            </div>

            <Tooltip title={copied ? "已复制" : "复制代码"}>
                <button className={styles.copyButton} onClick={handleCopy}>
                    {copied ? <CheckOutlined style={{ color: 'var(--hm-color-success)' }} /> : <CopyOutlined />}
                </button>
            </Tooltip>
        </div>
    );
};
