/**
 * PageContainer — 页面通用容器。
 *
 * 提供统一的页面结构: 标题 + 描述 + 操作按钮 + 内容区。
 * 所有页面必须使用此组件包裹，禁止自行构造页面头部。
 *
 * 用法:
 *   <PageContainer
 *     title="知识库管理"
 *     description="管理文档知识库，上传文档"
 *     actions={<Button type="primary">创建</Button>}
 *   >
 *     {children}
 *   </PageContainer>
 *
 * 基于: Ant Design Typography + Flex
 * @module components/common
 * @see REGISTRY.md > 前端 > 组件 > PageContainer
 */

import React from 'react';
import { Typography, Flex } from 'antd';
import styles from './PageContainer.module.css';

const { Title, Text } = Typography;

export interface PageContainerProps {
    /** 页面标题 */
    title: string;
    /** 页面描述 (副标题) */
    description?: string;
    /** 右上角操作按钮区 */
    actions?: React.ReactNode;
    /** 内容区最大宽度 (默认用 CSS 变量) */
    maxWidth?: number | string;
    /** 页面内容 */
    children: React.ReactNode;
}

export const PageContainer: React.FC<PageContainerProps> = ({
    title,
    description,
    actions,
    maxWidth,
    children,
}) => {
    return (
        <div className={styles.container} style={maxWidth ? { maxWidth } : undefined}>
            {/* 页面头部 */}
            <Flex justify="space-between" align="flex-start" className={styles.header}>
                <div>
                    <Title level={3} className={styles.title}>{title}</Title>
                    {description && (
                        <Text type="secondary" className={styles.description}>{description}</Text>
                    )}
                </div>
                {actions && <div className={styles.actions}>{actions}</div>}
            </Flex>

            {/* 内容区 */}
            <div className={styles.body}>
                {children}
            </div>
        </div>
    );
};
