/**
 * EmptyState — 统一空状态展示组件。
 *
 * 替代所有页面中独立编写的空状态 UI。
 *
 * 用法:
 *   <EmptyState
 *     icon={<DatabaseOutlined />}
 *     title="还没有知识库"
 *     description="点击创建按钮开始"
 *     action={<Button type="primary">创建</Button>}
 *   />
 *
 * @module components/common
 * @see REGISTRY.md > 前端 > 组件 > EmptyState
 */

import React from 'react';
import { Card, Typography, Flex } from 'antd';
import styles from './EmptyState.module.css';

const { Text, Title } = Typography;

export interface EmptyStateProps {
    /** 图标 */
    icon: React.ReactNode;
    /** 主要标题 */
    title: string;
    /** 描述文字 */
    description?: string;
    /** 操作按钮 */
    action?: React.ReactNode;
    /** 是否包裹在 Card 中 */
    wrapped?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
    icon,
    title,
    description,
    action,
    wrapped = true,
}) => {
    const content = (
        <Flex vertical align="center" gap={16} className={styles.container}>
            <div className={styles.iconWrap}>{icon}</div>
            <div className={styles.textArea}>
                <Title level={5} className={styles.title}>{title}</Title>
                {description && <Text type="secondary">{description}</Text>}
            </div>
            {action && <div className={styles.action}>{action}</div>}
        </Flex>
    );

    return wrapped ? <Card>{content}</Card> : content;
};
