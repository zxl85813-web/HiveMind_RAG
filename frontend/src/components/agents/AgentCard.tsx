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
import { Card, Typography, Flex, Tag, Tooltip, Divider, Button, Popconfirm } from 'antd';
import { ApiOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined, LockOutlined, ExperimentOutlined } from '@ant-design/icons';
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
    /** 绑定的 Skill 名称列表 */
    skills?: string[];
    /** 可用的 Tool 名称列表 */
    tools?: string[];
    /** 首选模型层级 */
    model_hint?: string | null;
    /** 是否为内置 Agent（不可编辑/删除） */
    built_in?: boolean;
    /** 编辑回调 */
    onEdit?: () => void;
    /** 删除回调 */
    onDelete?: () => void;
    /** 测试回调 */
    onTest?: () => void;
}

export const AgentCard: React.FC<AgentCardProps> = ({
    name,
    description,
    icon,
    status,
    currentTask,
    skills,
    tools,
    model_hint,
    built_in,
    onEdit,
    onDelete,
    onTest,
}) => {
    const hasRelations = (skills && skills.length > 0) || (tools && tools.length > 0);
    const showActions = onTest || (!built_in && (onEdit || onDelete));
    return (
        <Card hoverable className={styles.card}>
            <Flex vertical gap={8}>
                <Flex justify="space-between" align="center">
                    <Text strong className={styles.name}>
                        {icon} {name}
                        {built_in && (
                            <Tooltip title="内置 Agent，不可编辑/删除">
                                <LockOutlined style={{ marginLeft: 6, color: '#94A3B8', fontSize: 12 }} />
                            </Tooltip>
                        )}
                    </Text>
                    <Flex gap={6} align="center">
                        {model_hint && (
                            <Tag color="default" style={{ fontSize: 10, padding: '0 4px', lineHeight: '16px', margin: 0 }}>
                                {model_hint}
                            </Tag>
                        )}
                        <StatusTag status={status} />
                    </Flex>
                </Flex>
                <Text type="secondary" className={styles.desc}>{description}</Text>
                {currentTask && (
                    <Text type="secondary" className={styles.task}>
                        📌 {currentTask}
                    </Text>
                )}
                {hasRelations && (
                    <>
                        <Divider style={{ margin: '4px 0' }} />
                        {skills && skills.length > 0 && (
                            <Flex gap={4} wrap="wrap" align="center">
                                <Tooltip title="绑定的 Skills">
                                    <ThunderboltOutlined style={{ color: '#a855f7', fontSize: 12 }} />
                                </Tooltip>
                                {skills.map((s) => (
                                    <Tag key={s} color="purple" style={{ fontSize: 10, padding: '0 5px', lineHeight: '18px', margin: 0 }}>{s}</Tag>
                                ))}
                            </Flex>
                        )}
                        {tools && tools.length > 0 && (
                            <Flex gap={4} wrap="wrap" align="center" style={{ marginTop: skills && skills.length > 0 ? 4 : 0 }}>
                                <Tooltip title="可用的 MCP Tools">
                                    <ApiOutlined style={{ color: '#06b6d4', fontSize: 12 }} />
                                </Tooltip>
                                {tools.slice(0, 4).map((t) => (
                                    <Tag key={t} color="cyan" style={{ fontSize: 10, padding: '0 5px', lineHeight: '18px', margin: 0 }}>{t}</Tag>
                                ))}
                                {tools.length > 4 && (
                                    <Tooltip title={tools.slice(4).join(', ')}>
                                        <Tag color="default" style={{ fontSize: 10, padding: '0 5px', lineHeight: '18px', margin: 0 }}>+{tools.length - 4}</Tag>
                                    </Tooltip>
                                )}
                            </Flex>
                        )}
                    </>
                )}
                {showActions && (
                    <>
                        <Divider style={{ margin: '4px 0' }} />
                        <Flex gap={6} justify="flex-end">
                            {onTest && (
                                <Button size="small" type="primary" ghost icon={<ExperimentOutlined />} onClick={onTest}>测试</Button>
                            )}
                            {!built_in && onEdit && (
                                <Button size="small" type="text" icon={<EditOutlined />} onClick={onEdit}>编辑</Button>
                            )}
                            {!built_in && onDelete && (
                                <Popconfirm
                                    title={`删除 Agent "${name}"?`}
                                    description="下一次对话会重建调度图"
                                    onConfirm={onDelete}
                                    okType="danger"
                                >
                                    <Button size="small" type="text" danger icon={<DeleteOutlined />}>删除</Button>
                                </Popconfirm>
                            )}
                        </Flex>
                    </>
                )}
            </Flex>
        </Card>
    );
};
