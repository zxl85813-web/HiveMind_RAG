/**
 * AgentCard — 单个 Agent 状态卡片。
 *
 * 展示 Agent 的名称、描述、当前状态。
 * 从 AgentsPage 中拆出的领域子组件。
 *
 * @module components/agents
 * @see REGISTRY.md > 前端 > 组件 > AgentCard
 */

import React from 'react';
import { Card, Typography, Flex } from 'antd';
import { StatusTag } from '../common';
import styles from './AgentCard.module.css';

const { Text } = Typography;

export interface AgentCardProps {
    /** Agent 名称 */
    name: string;
    /** Agent 描述 */
    description: string;
    /** 图标 (emoji) */
    icon: string;
    /** 运行状态 */
    status: 'idle' | 'processing' | 'reflecting';
    /** 当前正在处理的任务 (可选) */
    currentTask?: string;
}

export const AgentCard: React.FC<AgentCardProps> = ({
    name,
    description,
    icon,
    status,
    currentTask,
}) => {
    return (
        <Card hoverable className={styles.card}>
            <Flex vertical gap={8}>
                <Flex justify="space-between" align="center">
                    <Text strong className={styles.name}>
                        {icon} {name}
                    </Text>
                    <StatusTag status={status} />
                </Flex>
                <Text type="secondary" className={styles.desc}>{description}</Text>
                {currentTask && (
                    <Text type="secondary" className={styles.task}>
                        📌 {currentTask}
                    </Text>
                )}
            </Flex>
        </Card>
    );
};
