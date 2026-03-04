import React from 'react';
import { Result, Alert, Button, Typography, Space } from 'antd';
import { SyncOutlined } from '@ant-design/icons';

const { Paragraph, Text } = Typography;

export interface ErrorDisplayProps {
    /** 错误的大标题 */
    title?: string;
    /** 主要错误信息 */
    message: string;
    /** 错误详情或堆栈（仅在有需要时展示） */
    details?: string;
    /** 展示类型：整页(page)或内联(inline) */
    type?: 'page' | 'inline';
    /** 重试回调函数 */
    onRetry?: () => void;
}

/**
 * 统一的错误展示组件
 * 
 * 适用于 API 请求失败、组件崩溃或找不到资源等异常状态的捕获及友好展示。
 */
export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
    title = '哎呀，出错了！',
    message,
    details,
    type = 'inline',
    onRetry
}) => {
    const extraContent = (
        <Space direction="vertical" style={{ width: '100%', textAlign: 'left', marginTop: type === 'page' ? 24 : 8 }}>
            {details && (
                <Paragraph type="secondary" style={{
                    background: 'var(--hm-color-bg-container-modal)',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    border: '1px solid var(--hm-color-border)',
                }}>
                    {details}
                </Paragraph>
            )}
            {onRetry && (
                <Button type="primary" icon={<SyncOutlined />} onClick={onRetry} style={{ marginTop: 8 }}>
                    重试
                </Button>
            )}
        </Space>
    );

    if (type === 'page') {
        return (
            <Result
                status="error"
                title={title}
                subTitle={<Text type="secondary">{message}</Text>}
                extra={extraContent}
            />
        );
    }

    // Inline display
    return (
        <Alert
            message={title}
            description={
                <div style={{ marginTop: 4 }}>
                    <Text>{message}</Text>
                    {extraContent}
                </div>
            }
            type="error"
            showIcon
            style={{ margin: '16px 0' }}
        />
    );
};
