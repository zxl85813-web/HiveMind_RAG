import React from 'react';
import { Row, Col, Typography, List, Tag, Badge, Space, Empty, Card, Tooltip, Flex, theme, Drawer, Divider, Timeline } from 'antd';
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
    DatabaseOutlined,
    InfoCircleOutlined,
    ToolOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer, StatCard, ErrorBoundary } from '../components/common';
import { AgentCard } from '../components/agents/AgentCard';
import { 
    useSwarmReflections, 
    useSwarmAgents, 
    useSwarmStats, 
    useSwarmTodos, 
    useSwarmTraces 
} from '../hooks/queries/useSwarmQuery';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { SwarmChatPanel } from '../components/agents/SwarmChatPanel';
import { useMonitor } from '../hooks/useMonitor';

const { Title, Text, Paragraph } = Typography;

const AgentDAGVisualizer = React.lazy(() => import('../components/agents/AgentDAGVisualizer'));

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
    const { track } = useMonitor();
    const [selectedTraceNode, setSelectedTraceNode] = React.useState<any>(null);

    React.useEffect(() => {
        track('system', 'page_load', { page: 'AgentsOverview' });
    }, [track]);
    
    // ...

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
                                <div className="markdown-todo-desc" style={{ marginBottom: 8, fontSize: '13px', color: 'var(--hm-color-text-tertiary)' }}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {item.description}
                                    </ReactMarkdown>
                                </div>
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
                            current_task={agent.current_task}
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
                <Col xs={24} lg={15}>
                    <Card
                        title={
                            <Space>
                                <span style={{ color: token.colorPrimary }}><MessageOutlined /> Swarm 交互中心 (Action Control)</span>
                                <Tag color="blue" variant="filled">LIVE SSE</Tag>
                            </Space>
                        }
                        style={{ borderRadius: '12px', border: 'var(--hm-border-subtle)' }}
                        bodyStyle={{ padding: 0 }}
                    >
                        <SwarmChatPanel />
                    </Card>
                </Col>
                <Col xs={24} lg={9}>
                    <Card
                        title={
                            <Space split={<Text type="secondary" style={{ fontWeight: 'normal' }}>|</Text>}>
                                <span style={{ color: token.colorInfo }}><ClusterOutlined /> Agent DAG 追踪</span>
                            </Space>
                        }
                        loading={loadingTraces && dagData.nodes.length === 0}
                        style={{ height: '100%', borderRadius: '12px', background: 'var(--hm-color-bg-elevated)', border: 'var(--hm-border-subtle)' }}
                        bodyStyle={{ padding: 0, height: '600px', display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center' }}
                    >
                        {dagData.nodes && dagData.nodes.length > 0 ? (
                            <ErrorBoundary fallback={<div style={{ padding: 20 }}><Empty description="图谱渲染发生冲突，请尝试刷新。" /></div>}>
                                <React.Suspense fallback={<Flex align="center" justify="center" style={{ height: '100%', width: '100%' }}><SyncOutlined spin /> &nbsp; Loading Chart...</Flex>}>
                                    <AgentDAGVisualizer 
                                        data={dagData} 
                                        height={590} 
                                        onNodeClick={(node) => setSelectedTraceNode(node)}
                                    />
                                </React.Suspense>
                            </ErrorBoundary>
                        ) : (
                            <div style={{ padding: '0 20px', textAlign: 'center' }}>
                                <Empty description="等待 Agent 集群产生执行链路 (在左侧发送指令以开启 Trace)" />
                            </div>
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

            {/* Trace Details Drawer */}
            <Drawer
                title={
                    <Space>
                        <Badge status={selectedTraceNode?.status?.toLowerCase().includes('success') ? 'success' : 'processing'} />
                        <span style={{ color: token.colorPrimary }}>执行详情 (Execution Trace)</span>
                    </Space>
                }
                placement="right"
                width={550}
                onClose={() => setSelectedTraceNode(null)}
                open={!!selectedTraceNode}
                styles={{
                    header: { background: 'var(--hm-color-bg-elevated)', borderBottom: '1px solid var(--hm-border-subtle)' },
                    body: { background: 'var(--hm-color-bg-layout)', padding: '16px' }
                }}
            >
                {selectedTraceNode && (
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        <Card size="small" style={{ background: 'var(--hm-glass-bg)', borderColor: 'var(--hm-color-brand-dim)' }}>
                            <Title level={5}>{selectedTraceNode.label}</Title>
                            <Space wrap>
                                <Tag color="blue"><ClusterOutlined /> {selectedTraceNode.agent}</Tag>
                                <Tag color={selectedTraceNode.status?.toLowerCase().includes('success') || selectedTraceNode.status === 'DONE' ? 'success' : 'warning'}>{selectedTraceNode.status.toUpperCase()}</Tag>
                                {selectedTraceNode.duration && <Tag color="default"><ClockCircleOutlined /> {selectedTraceNode.duration}</Tag>}
                            </Space>
                        </Card>

                        {/* 🧠 Related Knowledge & Memories (NEW!) */}
                        {(selectedTraceNode.details?.retrieved_doc_ids?.length > 0 || selectedTraceNode.details?.related_memories?.length > 0) && (
                            <div style={{ background: 'var(--hm-color-brand-dim)15', padding: '12px', borderRadius: '8px' }}>
                                <Text strong style={{ display: 'block', marginBottom: 8 }}><BulbOutlined /> 关联知识与背景 (Knowledge Context)</Text>
                                <Space wrap>
                                    {selectedTraceNode.details.related_memories?.map((m: any, i: number) => (
                                        <Tag key={i} color="processing" style={{ borderRadius: 12 }}>记忆: {m.id.slice(0, 8)}</Tag>
                                    ))}
                                    {selectedTraceNode.details.retrieved_doc_ids?.map((id: string, i: number) => (
                                        <Tag key={i} color="cyan" style={{ borderRadius: 12 }}>检索: {id.slice(0, 12)}...</Tag>
                                    ))}
                                </Space>
                            </div>
                        )}

                        <Divider orientation={"left" as any} style={{ margin: '8px 0' }}><BulbOutlined /> 决策逻辑 (Reasoning)</Divider>
                        <div style={{ background: 'var(--hm-color-bg-elevated)', padding: '12px', borderRadius: '8px', border: '1px solid var(--hm-border-subtle)' }}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {selectedTraceNode.details?.reasoning || selectedTraceNode.details?.thought_log || "暂无内部思考详情"}
                            </ReactMarkdown>
                        </div>

                        {selectedTraceNode.details?.instruction && (
                            <>
                                <Divider orientation={"left" as any} style={{ margin: '8px 0' }}><MessageOutlined /> 任务指令 (Instruction)</Divider>
                                <div style={{ fontSize: '12px', color: 'var(--hm-color-text-secondary)' }}>
                                    {selectedTraceNode.details.instruction}
                                </div>
                            </>
                        )}

                        {selectedTraceNode.details?.tool_calls && selectedTraceNode.details.tool_calls.length > 0 && (
                            <>
                                <Divider orientation={"left" as any} style={{ margin: '8px 0' }}><ToolOutlined /> 工具调用 (Tool Calls)</Divider>
                                <Timeline
                                    mode="left"
                                    items={selectedTraceNode.details.tool_calls.map((tc: any, idx: number) => ({
                                        color: 'blue',
                                        children: (
                                            <div key={idx}>
                                                <Text strong>{tc.name}</Text>
                                                <div style={{ marginTop: 4 }}>
                                                    <Text code style={{ fontSize: '11px' }}>Args: {JSON.stringify(tc.args)}</Text>
                                                </div>
                                                <div style={{ marginTop: 6, fontSize: '12px', color: 'var(--hm-color-text-secondary)' }}>
                                                    Result: {tc.result?.substring(0, 80)}...
                                                </div>
                                            </div>
                                        )
                                    }))}
                                />
                            </>
                        )}

                        <Divider orientation={"left" as any} style={{ margin: '8px 0' }}><DatabaseOutlined /> 原始元数据 (Raw JSON)</Divider>
                        <div style={{ maxHeight: '200px', overflow: 'auto' }}>
                             <pre style={{ fontSize: '10px', background: 'var(--hm-color-bg-elevated)', padding: '10px', borderRadius: '4px' }}>
                                 {JSON.stringify(selectedTraceNode.details, null, 2)}
                             </pre>
                        </div>
                    </Space>
                )}
            </Drawer>
        </PageContainer>
    );
};
