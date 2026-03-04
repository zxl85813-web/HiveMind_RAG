import React from 'react';
import { Spin, Typography, Space } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

const { Text } = Typography;

export interface LoadingStateProps {
    /** 自定义加载文案，默认为“加载中...” */
    tip?: string;
    /** 是否占满并垂直水平居中整个容器/屏幕 */
    fullScreen?: boolean;
    /** 自定义图标大小 */
    size?: number;
}

/**
 * 统一的加载态展示组件
 * 
 * 用于统一项目中各个板块的骨架或全局载入动画风格，保持 Cyber-Refined 的特色。
 */
export const LoadingState: React.FC<LoadingStateProps> = ({
    tip = '加载中...',
    fullScreen = false,
    size = 24
}) => {
    const spinnerIcon = (
        <LoadingOutlined style={{ fontSize: size, color: 'var(--hm-color-primary)' }} spin />
    );

    const content = (
        <Space direction="vertical" align="center" size="middle">
            <Spin indicator={spinnerIcon} />
            {tip && <Text type="secondary" style={{ fontSize: '13px', letterSpacing: '0.5px' }}>{tip}</Text>}
        </Space>
    );

    if (fullScreen) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '200px',
                height: '100%',
                width: '100%',
                padding: '40px 0'
            }}>
                {content}
            </div>
        );
    }

    return (
        <div style={{ textAlign: 'center', padding: '24px 0' }}>
            {content}
        </div>
    );
};
