import React from 'react';
import { Row, Col, Typography, List, Tag, Badge, Space, Empty, Card, Tooltip, Flex, theme } from 'antd';
import {
    ClusterOutlined,
    MessageOutlined,
    UnorderedListOutlined,
    ExperimentOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    SyncOutlined,
    BulbOutlined,
    CompassOutlined,
    ShareAltOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer, StatCard } from '../components/common';
import { AgentCard } from '../components/agents/AgentCard';
import { AgentDAGVisualizer } from '../components/agents/AgentDAGVisualizer';
import { 
    useSwarmReflections, 
    useSwarmAgents, 
    useSwarmStats, 
    useSwarmTodos, 
    useSwarmTraces 
} from '../hooks/queries/useSwarmQuery';

const { Title, Text, Paragraph } = Typography;

/**
 * 🛰️ [FE-GOV-001]: Agent 蜂巢监控页面 (Refactored with React Query)
 */
export const AgentsPage: React.FC = () => {
    const { t } = useTranslation();
    const { token } = theme.useToken();
    
    // Server State with Auto-refresh
    const { data: reflections = [], isLoading: loadingRefl } = useSwarmReflections();
    const { data: agents = [] } = useSwarmAgents();
    const { data: stats } = useSwarmStats();
    const { data: todos = [], isLoading: loadingTodos } = useSwarmTodos();
    const { data: dagData = { nodes: [], links: [] }, isLoading: loadingTraces, refetch, isRefetching } = useSwarmTraces();

    const renderTodoTab = () => (
        <List
            loading={loadingTodos}
            dataSource={todos}
            locale={{ emptyText: <Empty description="任务队列已排空。Agent 集群正处于待命状态。" /> }}
            renderItem={(item) => (
                <List.Item key={item.id} className="memory-log-item" style={{ padding: '12px 0' }}>
                    <List.Item.Meta
                        avatar={<Badge status={item.status === 'completed' ? 'success' : 'processing'} />}
                        title={
                            <Space>
                                <Text strong>{item.title}</Text>
                                <Tag color={
                                    item.priority === 'critical' ? 'red' :
                                        item.priority === 'high' ? 'orange' :
                                            item.priority === 'medium' ? 'blue' : 'default'
                                }>
                                    {item.priority.toUpperCase()}
                                </Tag>
                            </Space>
                        }
                        description={
                            <div style={{ marginTop: 8 }}>
                                <Paragraph type="secondary" style={{ marginBottom: 8, fontSize: '13px' }}>{item.description}</Paragraph>
                                <Space size="middle" separator={<Text type="secondary" style={{ fontSize: '10px' }}>|</Text>} wrap>
                                    <Text type="secondary" style={{ fontSize: '11px' }}>
                                        <BulbOutlined /> <Tag variant="filled" style={{ fontSize: '10px', padding: '0 4px', lineHeight: '16px' }}>{item.created_by}</Tag>
                                    </Text>
                                    <Text type="secondary" style={{ fontSize: '11px' }}>
                                        <CompassOutlined /> {item.assigned_to || '自动调度'}
                                    </Text>
                                    <Text type="secondary" style={{ fontSize: '11px' }}>
                                        <ClockCircleOutlined /> {new Date(item.created_at).toLocaleString()}
                                    </Text>
                                </Space>
                            </div>
                        }
                    />
                    <div style={{ textAlign: 'center', minWidth: 80 }}>
                        <Tag color={
                            item.status === 'completed' ? 'success' :
                                item.status === 'in_progress' ? 'processing' :
                                    item.status === 'waiting_user' ? 'warning' : 'default'
                        }>
                            {item.status.replace('_', ' ').toUpperCase()}
                        </Tag>
                    </div>
                </List.Item>
            )}
        />
    );

    const renderReflectionBoard = () => (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
            {reflections.length === 0 ? (
                <Empty description="Agent 群体尚未产生显著的自省洞察。" style={{ gridColumn: '1 / -1', padding: '40px 0' }} />
            ) : (
                reflections.map((item) => (
                    <Card key={item.id} size="small" hoverable style={{ borderColor: 'var(--hm-color-brand-dim)', background: 'var(--hm-glass-bg)' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Flex justify="space-between" align="flex-start">
                                <Space>
                                    <Text strong style={{ color: token.colorPrimary, fontSize: '13px' }}>Agent [{item.agent_name}]</Text>
                                    <Tag color="cyan" variant="filled" style={{ border: 'none' }}>{item.type.replace('_', ' ')}</Tag>
                                </Space>
                                <Tooltip title="Confidence Score">
                                    <Badge count={`${(item.confidence_score * 100).toFixed(0)}%`} style={{ backgroundColor: token.colorSuccess }} />
                                </Tooltip>
                            </Flex>

                            <Paragraph style={{ margin: '8px 0', fontSize: '13px', lineHeight: '1.6', color: 'var(--hm-color-text-primary)' }}>
                                {item.summary}
                            </Paragraph>

                            {item.action_taken && (
                                <div style={{ background: 'var(--hm-color-bg-elevated)', padding: '6px 10px', borderRadius: 4, borderLeft: `3px solid ${token.colorSuccess}` }}>
                                    <Text type="success" style={{ fontSize: '12px' }}>
                                        <CheckCircleOutlined style={{ marginRight: 4 }} />
                                        {item.action_taken}
                                    </Text>
                                </div>
                            )}

                            <Text type="secondary" style={{ fontSize: '11px', display: 'block', textAlign: 'right', marginTop: 4 }}>
                                <ClockCircleOutlined style={{ marginRight: 4 }} />
                                {new Date(item.created_at).toLocaleString()}
                            </Text>
                        </Space>
                    </Card>
                ))
            )}
        </div>
    );

    return (
        <PageContainer
            title={t('agents.title')}
            description={t('agents.description')}
            actions={
                <Tooltip title="刷新数据">
                    <SyncOutlined 
                        spin={isRefetching} 
                        onClick={() => refetch()} 
                        style={{ fontSize: 20, cursor: 'pointer', color: token.colorPrimary }} 
                    />
                </Tooltip>
            }
        >
            {/* 统计概览 */}
            <Row gutter={[16, 16]}>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.active')} value={stats?.active_agents || 0} icon={<ClusterOutlined />} color="primary" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.requests')} value={stats?.today_requests || 0} icon={<MessageOutlined />} color="info" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.todos')} value={stats?.shared_todos || 0} icon={<UnorderedListOutlined />} color="warning" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.reflections')} value={stats?.reflection_logs || 0} icon={<ExperimentOutlined />} color="success" />
                </Col>
            </Row>

            {/* Agent 列表 */}
            <Title level={4} style={{ marginTop: '24px' }}>
                <Badge dot status="processing" offset={[10, 0]}>
                    <ClusterOutlined /> {t('agents.clusters')}
                </Badge>
            </Title>
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

            <Title level={4} style={{ marginTop: '36px' }}>
                <Badge dot status="success" offset={[10, 0]}>
                    <ShareAltOutlined /> 蜂巢监控: 共享记忆与群智反思 (Shared Memory View)
                </Badge>
            </Title>

            <Row gutter={[24, 24]}>
                <Col xs={24}>
                    <Card
                        title={
                            <Space split={<Text type="secondary" style={{ fontWeight: 'normal' }}>|</Text>}>
                                <span style={{ color: token.colorInfo }}><ClusterOutlined /> Agent DAG 实时链路追踪 (Execution Trace)</span>
                                <Text type="secondary" style={{ fontSize: '12px', fontWeight: 'normal' }}>
                                    可视化展示 Agent 之间的协作流水线与数据流转状态
                                </Text>
                            </Space>
                        }
                        loading={loadingTraces && dagData.nodes.length === 0}
                        style={{ borderRadius: '12px', background: 'var(--hm-color-bg-elevated)', border: 'var(--hm-border-subtle)' }}
                        bodyStyle={{ padding: 0, height: '440px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
                    >
                        {dagData.nodes && dagData.nodes.length > 0 ? (
                            <AgentDAGVisualizer data={dagData} height={440} />
                        ) : (
                            <Empty description="等待 Agent 集群产生执行链路 (在侧边栏对话以生成 Trace)" />
                        )}
                    </Card>
                </Col>
            </Row>

            <Row gutter={[24, 24]} style={{ marginTop: '24px' }}>
                <Col xs={24} lg={16}>
                    <Card
                        title={<span style={{ color: token.colorPrimary }}><ExperimentOutlined /> 共享记忆板 (Reflections & Active Memory)</span>}
                        style={{ height: '100%', borderRadius: '12px' }}
                        loading={loadingRefl && reflections.length === 0}
                    >
                        {renderReflectionBoard()}
                    </Card>
                </Col>
                <Col xs={24} lg={8}>
                    <Card
                        title={<><UnorderedListOutlined /> 协同任务队列 (Todos)</>}
                        style={{ height: '100%', borderRadius: '12px' }}
                        bodyStyle={{ paddingRight: 8 }}
                        loading={loadingTodos && todos.length === 0}
                    >
                        <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                            {renderTodoTab()}
                        </div>
                    </Card>
                </Col>
            </Row>
        </PageContainer>
    );
};
