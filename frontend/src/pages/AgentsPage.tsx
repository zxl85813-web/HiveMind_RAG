import React, { useEffect, useState } from 'react';
import { Row, Col, Typography, List, Tag, Badge, Space, Empty, Card, Tooltip, Flex, Button, Modal, Form, Input, Select, message } from 'antd';
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
    ShareAltOutlined,
    ApartmentOutlined,
    PlusOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer, StatCard } from '../components/common';
import { AgentCard } from '../components/agents/AgentCard';
import { AgentDAGVisualizer } from '../components/agents/AgentDAGVisualizer';
import { SwarmTopologyMap } from '../components/agents/SwarmTopologyMap';
import type { DAGData } from '../components/agents/AgentDAGVisualizer';
import { agentApi, type ReflectionEntry, type AgentInfo, type SwarmStats, type TodoItem, type TopologyData } from '../services/agentApi';

const { Title, Text, Paragraph } = Typography;

export const AgentsPage: React.FC = () => {
    const { t } = useTranslation();
    const [reflections, setReflections] = useState<ReflectionEntry[]>([]);
    const [agents, setAgents] = useState<AgentInfo[]>([]);
    const [stats, setStats] = useState<SwarmStats>({
        active_agents: 0,
        today_requests: 0,
        shared_todos: 0,
        reflection_logs: 0
    });
    const [todos, setTodos] = useState<TodoItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [dagData, setDagData] = useState<DAGData>({ nodes: [], links: [] });
    const [topologyData, setTopologyData] = useState<TopologyData>({ nodes: [], links: [] });
    const [topologyLoading, setTopologyLoading] = useState(false);

    // === Agent CRUD ===
    const [agentModalOpen, setAgentModalOpen] = useState(false);
    const [agentModalMode, setAgentModalMode] = useState<'create' | 'update'>('create');
    const [agentSubmitting, setAgentSubmitting] = useState(false);
    const [agentForm] = Form.useForm<{ name: string; description: string; model_hint: string; skillsText: string }>();

    const fetchData = async () => {
        setLoading(true);
        try {
            const [reflRes, agentsRes, statsRes, todosRes, traceRes] = await Promise.all([
                agentApi.getReflections(20),
                agentApi.getAgents(),
                agentApi.getStats(),
                agentApi.getTodos(),
                agentApi.getTraces()
            ]);

            setReflections(reflRes.data.data || []);
            setAgents(agentsRes.data.data || []);
            setStats(statsRes.data.data || { active_agents: 0, today_requests: 0, shared_todos: 0, reflection_logs: 0 });
            setTodos(todosRes.data.data || []);

            const liveTrace = traceRes.data.data;
            if (liveTrace && liveTrace.nodes && liveTrace.nodes.length > 0) {
                setDagData(liveTrace);
            } else {
                // Keep the state empty if no traces yet, but maybe show a placeholder text in the visualizer?
                setDagData({ nodes: [], links: [] });
            }
        } catch (err) {
            console.error('Failed to fetch swarm data:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchTopology = async () => {
        setTopologyLoading(true);
        try {
            const res = await agentApi.getTopology();
            setTopologyData(res.data.data || { nodes: [], links: [] });
        } catch (err) {
            console.error('Failed to fetch topology:', err);
        } finally {
            setTopologyLoading(false);
        }
    };

    const openCreateAgent = () => {
        setAgentModalMode('create');
        agentForm.resetFields();
        agentForm.setFieldsValue({ model_hint: 'balanced' });
        setAgentModalOpen(true);
    };

    const openEditAgent = (agent: AgentInfo) => {
        setAgentModalMode('update');
        agentForm.setFieldsValue({
            name: agent.name,
            description: agent.description,
            model_hint: agent.model_hint || 'balanced',
            skillsText: (agent.skills || []).join(', '),
        });
        setAgentModalOpen(true);
    };

    const submitAgent = async () => {
        const values = await agentForm.validateFields();
        const skills = values.skillsText
            ? values.skillsText.split(/[,、\s]+/).filter(Boolean)
            : [];
        setAgentSubmitting(true);
        try {
            await agentApi.upsertAgent({
                name: values.name.trim(),
                description: values.description.trim(),
                skills,
                model_hint: values.model_hint || null,
            });
            message.success(`Agent 已${agentModalMode === 'create' ? '创建' : '更新'}`);
            setAgentModalOpen(false);
            await Promise.all([fetchData(), fetchTopology()]);
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '保存失败');
            console.error(e);
        } finally {
            setAgentSubmitting(false);
        }
    };

    const deleteAgent = async (name: string) => {
        try {
            await agentApi.deleteAgent(name);
            message.success(`已删除 Agent: ${name}`);
            await Promise.all([fetchData(), fetchTopology()]);
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '删除失败');
            console.error(e);
        }
    };

    useEffect(() => {
        fetchData();
        fetchTopology();
        const timer = setInterval(fetchData, 10000); // Refresh every 10s
        return () => clearInterval(timer);
    }, []);

    const renderTodoTab = () => (
        <List
            loading={loading}
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
                    <Card key={item.id} size="small" hoverable style={{ borderColor: 'rgba(6, 214, 160, 0.2)', background: 'rgba(255, 255, 255, 0.03)' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Flex justify="space-between" align="flex-start">
                                <Space>
                                    <Text strong style={{ color: '#06D6A0', fontSize: '13px' }}>Agent [{item.agent_name}]</Text>
                                    <Tag color="cyan" variant="filled" style={{ border: 'none' }}>{item.type.replace('_', ' ')}</Tag>
                                </Space>
                                <Tooltip title="Confidence Score">
                                    <Badge count={`${(item.confidence_score * 100).toFixed(0)}%`} style={{ backgroundColor: '#52c41a' }} />
                                </Tooltip>
                            </Flex>

                            <Paragraph style={{ margin: '8px 0', fontSize: '13px', lineHeight: '1.6', color: 'var(--hm-color-text-primary)' }}>
                                {item.summary}
                            </Paragraph>

                            {item.action_taken && (
                                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '6px 10px', borderRadius: 4, borderLeft: '3px solid #52c41a' }}>
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
                <Tooltip title="更新数据">
                    <SyncOutlined spin={loading} onClick={fetchData} style={{ fontSize: 20, cursor: 'pointer', color: '#06D6A0' }} />
                </Tooltip>
            }
        >
            {/* 统计概览 */}
            <Row gutter={[16, 16]}>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.active')} value={stats.active_agents} icon={<ClusterOutlined />} color="primary" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.requests')} value={stats.today_requests} icon={<MessageOutlined />} color="info" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.todos')} value={stats.shared_todos} icon={<UnorderedListOutlined />} color="warning" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title={t('agents.stats.reflections')} value={stats.reflection_logs} icon={<ExperimentOutlined />} color="success" />
                </Col>
            </Row>

            {/* Agent 列表 */}
            <Flex justify="space-between" align="center" style={{ marginTop: '24px' }}>
                <Title level={4} style={{ margin: 0 }}>
                    <Badge dot status="processing" offset={[10, 0]}>
                        <ClusterOutlined /> {t('agents.clusters')}
                    </Badge>
                </Title>
                <Button type="primary" icon={<PlusOutlined />} onClick={openCreateAgent}>
                    添加 Agent
                </Button>
            </Flex>
            <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
                {agents.map((agent) => (
                    <Col key={agent.name} xs={24} sm={12} lg={8}>
                        <AgentCard
                            name={agent.name}
                            description={agent.description}
                            icon={agent.icon}
                            status={agent.status}
                            skills={agent.skills}
                            tools={agent.tools}
                            model_hint={agent.model_hint}
                            built_in={agent.built_in}
                            onEdit={() => openEditAgent(agent)}
                            onDelete={() => deleteAgent(agent.name)}
                        />
                    </Col>
                ))}
            </Row>

            {/* 能力拓扑图 */}
            <Title level={4} style={{ marginTop: '36px' }}>
                <Badge dot status="warning" offset={[10, 0]}>
                    <ApartmentOutlined /> 能力拓扑图 (Capability Topology)
                </Badge>
            </Title>
            <Card
                title={
                    <Space split={<Text type="secondary" style={{ fontWeight: 'normal' }}>|</Text>}>
                        <span style={{ color: '#a855f7' }}><ApartmentOutlined /> Agent → Skill → Tool 关系图谱</span>
                        <Text type="secondary" style={{ fontSize: '12px', fontWeight: 'normal' }}>
                            可视化展示每个 Agent 绑定的 Skill 能力包与可调用的 MCP 工具
                        </Text>
                    </Space>
                }
                extra={
                    <Tooltip title="刷新拓扑">
                        <SyncOutlined spin={topologyLoading} onClick={fetchTopology} style={{ cursor: 'pointer', color: '#a855f7' }} />
                    </Tooltip>
                }
                style={{ borderRadius: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid #1f1f1f' }}
                styles={{ body: { padding: 0, height: '480px', overflow: 'hidden', borderRadius: '0 0 12px 12px' } }}
            >
                {topologyData.nodes.length > 0 ? (
                    <SwarmTopologyMap data={topologyData} height={480} />
                ) : (
                    <Flex justify="center" align="center" style={{ height: '100%' }}>
                        <Empty description="暂无能力拓扑数据 (Agent 未注册 Skill 或 Tool)" />
                    </Flex>
                )}
            </Card>

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
                                <span style={{ color: '#1890ff' }}><ClusterOutlined /> Agent DAG 实时链路追踪 (Execution Trace)</span>
                                <Text type="secondary" style={{ fontSize: '12px', fontWeight: 'normal' }}>
                                    可视化展示 Agent 之间的协作流水线与数据流转状态
                                </Text>
                            </Space>
                        }
                        style={{ borderRadius: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid #1f1f1f' }}
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
                        title={<span style={{ color: '#06D6A0' }}><ExperimentOutlined /> 共享记忆板 (Reflections & Active Memory)</span>}
                        style={{ height: '100%', borderRadius: '12px' }}
                    >
                        {renderReflectionBoard()}
                    </Card>
                </Col>
                <Col xs={24} lg={8}>
                    <Card
                        title={<><UnorderedListOutlined /> 协同任务队列 (Todos)</>}
                        style={{ height: '100%', borderRadius: '12px' }}
                        bodyStyle={{ paddingRight: 8 }}
                    >
                        <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                            {renderTodoTab()}
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* Agent 添加/编辑 Modal */}
            <Modal
                title={<Space><PlusOutlined /> {agentModalMode === 'create' ? '添加 Agent' : '编辑 Agent'}</Space>}
                open={agentModalOpen}
                onCancel={() => setAgentModalOpen(false)}
                onOk={submitAgent}
                confirmLoading={agentSubmitting}
                okText={agentModalMode === 'create' ? '创建' : '保存'}
                width={580}
                destroyOnClose
            >
                <Form form={agentForm} layout="vertical" preserve={false}>
                    <Form.Item
                        name="name"
                        label="Agent 名称"
                        rules={[
                            { required: true, message: '请输入 agent 名称' },
                            { pattern: /^[a-z][a-z0-9_]*$/i, message: '只允许字母/数字/下划线，且字母开头' },
                        ]}
                        extra="作为 Supervisor 路由时的唯一标识"
                    >
                        <Input placeholder="data_analyst" disabled={agentModalMode === 'update'} />
                    </Form.Item>
                    <Form.Item
                        name="description"
                        label="能力描述"
                        rules={[{ required: true, message: '请输入描述' }]}
                        extra="Supervisor 会根据这段描述决定何时调度该 Agent，请尽量准确"
                    >
                        <Input.TextArea rows={3} placeholder="负责数据分析、统计建模和图表生成。" />
                    </Form.Item>
                    <Form.Item name="model_hint" label="模型层级" initialValue="balanced">
                        <Select
                            options={[
                                { value: 'fast', label: 'Fast — 低延迟轻量模型' },
                                { value: 'balanced', label: 'Balanced — 通用模型 (默认)' },
                                { value: 'reasoning', label: 'Reasoning — 推理增强模型' },
                            ]}
                        />
                    </Form.Item>
                    <Form.Item
                        name="skillsText"
                        label="绑定的 Skills (用逗号分隔)"
                        extra="Skill 名称需在能力中心存在，否则将被忽略"
                    >
                        <Input placeholder="rag_qa, doc_summary" />
                    </Form.Item>
                </Form>
            </Modal>
        </PageContainer>
    );
};
