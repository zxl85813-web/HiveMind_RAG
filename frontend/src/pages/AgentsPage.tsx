/**
 * AgentsPage — Agent 监控面板。
 *
 * 使用通用组件: PageContainer, StatCard
 * 使用领域组件: AgentCard
 *
 * @module pages
 * @see REGISTRY.md > 前端 > 页面 > AgentsPage
 * @see docs/requirements/REQ-001-agent-swarm.md
 */

import React, { useEffect, useState } from 'react';
import { Row, Col, Typography, List, Tag, Badge, Space } from 'antd';
import { ClusterOutlined, MessageOutlined, UnorderedListOutlined, ExperimentOutlined, CheckCircleOutlined, ClockCircleOutlined, ToolOutlined } from '@ant-design/icons';
import { PageContainer, StatCard } from '../components/common';
import { AgentCard } from '../components/agents/AgentCard';
import { agentApi, type ReflectionEntry, type AgentInfo, type SwarmStats } from '../services/agentApi';
import api from '../services/api';

const { Title, Text } = Typography;

export const AgentsPage: React.FC = () => {
    const [reflections, setReflections] = useState<ReflectionEntry[]>([]);
    const [agents, setAgents] = useState<AgentInfo[]>([]);
    const [stats, setStats] = useState<SwarmStats>({
        active_agents: 0,
        today_requests: 0,
        shared_todos: 0,
        reflection_logs: 0
    });
    const [todos, setTodos] = useState<any[]>([]);

    const fetchData = () => {
        agentApi.getReflections(10).then(res => setReflections(res.data.data)).catch(console.error);
        agentApi.getAgents().then(res => setAgents(res.data.data)).catch(console.error);
        agentApi.getStats().then(res => setStats(res.data.data)).catch(console.error);
        // We'll mock the todos list fetching here too
        api.get('/agents/swarm/todos').then(res => setTodos(res.data.data)).catch(console.error);
    };

    useEffect(() => {
        fetchData();

        // Polling every 5s
        const timer = setInterval(fetchData, 5000);
        return () => clearInterval(timer);
    }, []);

    return (
        <PageContainer
            title="Agent 蜂巢监控"
            description="实时监控 Agent Swarm 的运行状态、共享记忆和 TODO 列表"
        >
            {/* 统计概览 — 使用共通 StatCard */}
            <Row gutter={[16, 16]}>
                <Col xs={12} lg={6}>
                    <StatCard title="活跃 Agent" value={stats.active_agents} icon={<ClusterOutlined />} color="primary" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title="今日请求" value={stats.today_requests} icon={<MessageOutlined />} color="info" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title="共享 TODO" value={stats.shared_todos} icon={<UnorderedListOutlined />} color="warning" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title="自省记录" value={stats.reflection_logs} icon={<ExperimentOutlined />} color="success" />
                </Col>
            </Row>

            {/* Agent 列表 — 使用领域 AgentCard */}
            <Row gutter={[16, 16]}>
                {agents.map((agent) => (
                    <Col key={agent.name} xs={24} sm={12} lg={8}>
                        <AgentCard
                            name={agent.name}
                            description={agent.description}
                            icon={agent.icon}
                            status={agent.status}
                        />
                    </Col>
                ))}
            </Row>

            {/* TODO List */}
            <Title level={4} style={{ marginTop: '2rem' }}><UnorderedListOutlined /> 共享任务队列 (Collective TODOs)</Title>
            <List
                style={{ background: 'var(--hm-glass-bg)', backdropFilter: 'var(--hm-glass-blur)', borderRadius: 'var(--hm-radius-lg)', marginTop: '1rem' }}
                bordered
                dataSource={todos}
                renderItem={(item) => (
                    <List.Item>
                        <List.Item.Meta
                            title={
                                <span>
                                    <Text strong>{item.title}</Text>
                                    <Tag color={item.priority === 'high' ? 'error' : item.priority === 'medium' ? 'warning' : 'default'} style={{ marginLeft: 8 }}>
                                        {item.priority.toUpperCase()}
                                    </Tag>
                                </span>
                            }
                            description={
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    <Text type="secondary">{item.description}</Text>
                                    <Space size="middle">
                                        <Text style={{ fontSize: '0.85em' }}><ToolOutlined /> By: {item.created_by}</Text>
                                        <Text style={{ fontSize: '0.85em' }}><ClockCircleOutlined /> Assigned To: {item.assigned_to}</Text>
                                    </Space>
                                </div>
                            }
                        />
                        <Tag color={item.status === 'completed' ? 'success' : item.status === 'in_progress' ? 'processing' : 'default'}>
                            {item.status.toUpperCase()}
                        </Tag>
                    </List.Item>
                )}
                locale={{ emptyText: 'All tasks completed. Swarm waiting for input.' }}
            />

            {/* Reflection List */}
            <Title level={4} style={{ marginTop: '2rem' }}>自省日志 (Thoughts & Reflections)</Title>
            <List
                style={{ background: 'var(--hm-glass-bg)', backdropFilter: 'var(--hm-glass-blur)', borderRadius: 'var(--hm-radius-lg)' }}
                bordered
                dataSource={reflections}
                renderItem={(item) => (
                    <List.Item>
                        <List.Item.Meta
                            avatar={
                                <Badge status={item.confidence_score > 0.8 ? "success" : "warning"} />
                            }
                            title={
                                <span>
                                    <Text strong>{item.agent_name}</Text>{' '}
                                    <Tag color="processing" style={{ marginLeft: 8 }}>{item.type}</Tag>
                                </span>
                            }
                            description={
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    <Text>{item.summary}</Text>
                                    {item.action_taken && (
                                        <Text type="secondary" style={{ fontSize: '0.85em' }}>
                                            <CheckCircleOutlined style={{ marginRight: 4, color: 'var(--hm-color-success)' }} />
                                            Action: {item.action_taken}
                                        </Text>
                                    )}
                                </div>
                            }
                        />
                        <div style={{ textAlign: 'right' }}>
                            <Text type="secondary" style={{ fontSize: '0.8em' }}>
                                Confidence: {(item.confidence_score * 100).toFixed(0)}%
                            </Text>
                            <br />
                            <Text type="secondary" style={{ fontSize: '0.8em' }}>
                                {new Date(item.created_at).toLocaleTimeString()}
                            </Text>
                        </div>
                    </List.Item>
                )}
                locale={{ emptyText: 'Agent Swarm is sleeping. No recent thoughts.' }}
            />
        </PageContainer>
    );
};
