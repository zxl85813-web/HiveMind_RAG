import React, { useState } from 'react';
import { Table, Tag, Card, Typography, Modal, Space, Timeline, Badge, Flex, theme, Button, Tabs, Empty, Tooltip, Row, Col } from 'antd';
import { 
    BugOutlined, 
    ThunderboltOutlined, 
    ShareAltOutlined, 
    FileSearchOutlined, 
    NodeIndexOutlined, 
    SearchOutlined,
    ClockCircleOutlined,
    SafetyCertificateOutlined,
    CheckCircleOutlined,
    ExperimentOutlined,
    CompressOutlined,
    RetweetOutlined,
    RocketOutlined,
    GlobalOutlined,
    RadarChartOutlined,
    DeploymentUnitOutlined,
    PartitionOutlined
} from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { useTraces } from '../hooks/queries/useDashboardQuery';
import { useSwarmTraces } from '../hooks/queries/useSwarmQuery';
import { AgentDAGVisualizer } from '../components/agents/AgentDAGVisualizer';
import { useMonitor } from '../hooks/useMonitor';

const { Text, Title, Paragraph } = Typography;

// [Arachne Tiering]: Mapping steps to icons and colors
const STEP_CONFIG: Record<string, { icon: React.ReactNode, color: string, label: string }> = {
    "QueryPreProcessingStep": { icon: <RetweetOutlined />, color: '#1890ff', label: '查询改写' },
    "ArachneRouterStep": { icon: <PartitionOutlined />, color: '#722ed1', label: 'Arachne 智能分流' },
    "GraphRetrievalStep": { icon: <NodeIndexOutlined />, color: '#eb2f96', label: '知识图谱检索' },
    "SqlSummaryFirstStep": { icon: <FileSearchOutlined />, color: '#fa8c16', label: 'SQL 摘要检索' },
    "SearchSubagentsStep": { icon: <RocketOutlined />, color: '#52c41a', label: '子代理并行检索' },
    "RRFHybridStep": { icon: <ExperimentOutlined />, color: '#13c2c2', label: 'RRF 混合检索' },
    "TruthAlignmentStep": { icon: <SafetyCertificateOutlined />, color: '#52c41a', label: '真相对齐' },
    "AclFilterStep": { icon: <BugOutlined />, color: '#faad14', label: 'ACL 权限过滤' },
    "RerankingStep": { icon: <ThunderboltOutlined />, color: '#fadb14', label: '交叉编码重排' },
    "ParentChunkExpansionStep": { icon: <SearchOutlined />, color: '#2f54eb', label: '父分片扩展' },
    "ContextualCompressionStep": { icon: <CompressOutlined />, color: '#fa541c', label: '上下文压缩' },
    "PromptInjectionFilterStep": { icon: <SafetyCertificateOutlined />, color: '#f5222d', label: '安全注入防御' },
    "Pipeline": { icon: <CheckCircleOutlined />, color: '#d9d9d9', label: '管道流水线' }
};

export const TracePage: React.FC = () => {
    const { track } = useMonitor();

    React.useEffect(() => {
        track('system', 'page_load', { page: 'TraceViewer_v2' });
    }, [track]);

    const { token } = theme.useToken();
    const { data: traces, isLoading: isLoadingTraces, error: tracesError } = useTraces();
    const { data: swarmDag, isLoading: isLoadingSwarm } = useSwarmTraces();
    
    const [selectedTrace, setSelectedTrace] = useState<any>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('rag');

    const ragColumns = [
        {
            title: '时间',
            dataIndex: 'created_at',
            key: 'time',
            render: (t: string) => new Date(t).toLocaleTimeString(),
            width: 100
        },
        {
            title: '意图 / 问题 (Intent & Query)',
            key: 'query_intent',
            render: (_: any, record: any) => (
                <Space direction="vertical" size={0}>
                    <Text strong>{record.query}</Text>
                    {record.intent_predicted && (
                        <Tag color="cyan" style={{ fontSize: '10px', height: '18px', lineHeight: '16px' }}>
                            <RadarChartOutlined /> {record.intent_predicted.toUpperCase()}
                        </Tag>
                    )}
                </Space>
            )
        },
        {
            title: 'Arachne 策略',
            dataIndex: 'retrieval_strategy',
            key: 'strategy',
            render: (s: string, record: any) => (
                <Space>
                    <Tag color="blue" bordered={false}>{s.toUpperCase()}</Tag>
                    {record.prefetch_hit && (
                        <Tooltip title="命中预取缓存 (Prefetch Hit)">
                            <RocketOutlined style={{ color: token.colorSuccess }} />
                        </Tooltip>
                    )}
                </Space>
            ),
            width: 150
        },
        {
            title: '命中数',
            dataIndex: 'total_found',
            key: 'found',
            align: 'center' as const,
            render: (n: number) => <Badge count={n} showZero color={n > 0 ? token.colorSuccess : token.colorError} />
        },
        {
            title: '延迟 (ms)',
            dataIndex: 'latency_ms',
            key: 'latency',
            render: (ms: number) => <Tag icon={<ClockCircleOutlined />} color={ms > 500 ? 'orange' : 'green'}>{Math.round(ms)}</Tag>,
            width: 110
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: any) => (
                <Button 
                    type="link" 
                    icon={<ShareAltOutlined />} 
                    onClick={() => {
                        setSelectedTrace(record);
                        setIsDetailOpen(true);
                    }}
                >
                    追踪
                </Button>
            ),
            width: 100
        }
    ];

    const parseStepTraces = (tracesArray: string[]) => {
        if (!tracesArray || tracesArray.length === 0) return [];

        return tracesArray.map(log => {
            const match = log.match(/^\[(.*?)\] (.*)$/);
            if (match) {
                const stepName = match[1];
                const content = match[2];
                return {
                    name: stepName,
                    content: content,
                    config: STEP_CONFIG[stepName] || { icon: <ExperimentOutlined />, color: token.colorTextQuaternary, label: stepName }
                };
            }
            return {
                name: 'Unknown',
                content: log,
                config: { icon: <ExperimentOutlined />, color: token.colorTextQuaternary, label: '未知环节' }
            };
        });
    };

    const renderRagTab = () => {
        // [FE-STABILITY-FIX]: Ant Design Table dataSource MUST be an array.
        // If traces.data exists but is not an array, Table will crash with "rawData.some is not a function".
        const rawData = (traces as any)?.data;
        const safeData = Array.isArray(rawData) ? rawData : [];

        return (
            <Card bordered={false} styles={{ body: { padding: 0 } }} style={{ borderRadius: 16, overflow: 'hidden', background: token.colorBgContainer }}>
                <Table
                    dataSource={safeData}
                    columns={ragColumns}
                    rowKey="id"
                    loading={isLoadingTraces}
                    pagination={{ pageSize: 12 }}
                    style={{ background: 'transparent' }}
                    locale={{ emptyText: tracesError ? `加载失败: ${(tracesError as any).message}` : '暂无数据' }}
                />
            </Card>
        );
    };

    const renderSwarmTab = () => (
        <div style={{ height: 'calc(100vh - 300px)', minHeight: '600px' }}>
            <Card 
                title={
                    <Space>
                        <DeploymentUnitOutlined style={{ color: token.colorPrimary }} />
                        <span>智体交互图追踪 (Swarm Execution Graph)</span>
                        <Tag color="processing">REAL-TIME</Tag>
                    </Space>
                }
                extra={
                    <Space>
                        <Text type="secondary" style={{ fontSize: '12px' }}>显示最近 5 分钟内的全链路执行流</Text>
                        <Button size="small" icon={<RetweetOutlined />} onClick={() => window.location.reload()}>强制重连</Button>
                    </Space>
                }
                style={{ height: '100%', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)', background: 'var(--hm-glass-bg)' }}
                styles={{ body: { height: 'calc(100% - 58px)', padding: 0 } }}
            >
                {swarmDag?.nodes && swarmDag.nodes.length > 0 ? (
                    <AgentDAGVisualizer data={swarmDag} />
                ) : (
                    <Flex vertical align="center" justify="center" style={{ height: '100%' }}>
                        <Empty 
                            image={Empty.PRESENTED_IMAGE_SIMPLE} 
                            description={
                                <Space direction="vertical">
                                    <Text type="secondary">{isLoadingSwarm ? '计算图中...' : '暂无活跃的智体执行链路'}</Text>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>在对话页面发送复杂指令，以激活 Swarm 多智能体并行任务。</Text>
                                </Space>
                            } 
                        />
                    </Flex>
                )}
            </Card>
        </div>
    );


    return (
        <PageContainer
            title="观测中心: 全链路追踪 (Trace Hub)"
            description="[L5 Governance] 实现 RAG 流水线与 Swarm 智体执行链路的深度透视，助力架构持续进化。"
        >
            <Tabs 
                activeKey={activeTab} 
                onChange={setActiveTab}
                items={[
                    {
                        key: 'rag',
                        label: <Space><RadarChartOutlined />RAG 流水线 (Pipeline)</Space>,
                        children: renderRagTab()
                    },
                    {
                        key: 'swarm',
                        label: <Space><DeploymentUnitOutlined />智体执行图 (Execution Graph)</Space>,
                        children: renderSwarmTab()
                    }
                ]}
                style={{ marginBottom: 24 }}
            />

            <Modal
                title={
                    <Flex align="center" gap={8}>
                        <NodeIndexOutlined style={{ color: token.colorPrimary }} />
                        <span>RAG 意识流全链路追踪 — ID: {selectedTrace?.id.slice(0, 8)}</span>
                    </Flex>
                }
                open={isDetailOpen}
                onCancel={() => setIsDetailOpen(false)}
                footer={null}
                width={850}
                styles={{ body: { padding: '24px', background: token.colorBgContainer } }}
            >
                {selectedTrace && (
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        <Card size="small" style={{ background: 'rgba(255,255,255,0.02)', border: `1px solid ${token.colorBorderSecondary}`, borderRadius: 12 }}>
                            <Row gutter={24}>
                                <Col span={18}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>用户原始提问</Text>
                                    <Title level={4} style={{ margin: '4px 0 0 0', color: token.colorPrimary }}>{selectedTrace.query}</Title>
                                </Col>
                                <Col span={6} style={{ textAlign: 'right' }}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>意图预测</Text>
                                    <div style={{ marginTop: 4 }}>
                                        <Tag color="cyan">{selectedTrace.intent_predicted?.toUpperCase() || 'GENERAL'}</Tag>
                                    </div>
                                </Col>
                            </Row>
                        </Card>

                        <Timeline
                            mode="left"
                            items={parseStepTraces(selectedTrace.step_traces).map((step, idx) => ({
                                color: step.config.color,
                                label: <Text type="secondary" style={{ fontSize: 11 }}>P{idx + 1}</Text>,
                                children: (
                                    <div style={{ marginBottom: 20 }}>
                                        <Flex align="center" gap={8} style={{ marginBottom: 8 }}>
                                            <span style={{ 
                                                display: 'inline-flex', 
                                                padding: '6px', 
                                                borderRadius: '8px', 
                                                background: `${step.config.color}18`, 
                                                color: step.config.color 
                                            }}>
                                                {step.config.icon}
                                            </span>
                                            <Text strong style={{ fontSize: 14 }}>{step.config.label}</Text>
                                            <Text type="secondary" style={{ fontSize: 11, background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: 4 }}>{step.name}</Text>
                                        </Flex>
                                        <Card size="small" style={{ borderRadius: 10, background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.05)' }}>
                                            <pre style={{ margin: 0, fontSize: 12, fontFamily: 'Fira Code, monospace', whiteSpace: 'pre-wrap', color: 'rgba(255,255,255,0.85)' }}>
                                                {step.content}
                                            </pre>
                                        </Card>
                                    </div>
                                ),
                                dot: <div style={{ 
                                    width: 14, height: 14, borderRadius: '50%', 
                                    background: step.config.color,
                                    border: `3px solid ${token.colorBgContainer}`,
                                    boxShadow: `0 0 8px ${step.config.color}`
                                }} />
                            }))}
                        />

                        {selectedTrace.retrieved_doc_ids?.length > 0 && (
                            <div style={{ marginTop: 8 }}>
                                <Title level={5} style={{ fontSize: 14 }}><FileSearchOutlined /> 最终检索命中文档 (Reference Docs)</Title>
                                <Flex wrap="wrap" gap={8}>
                                    {selectedTrace.retrieved_doc_ids.map((docId: string) => (
                                        <Tag key={docId} color="default" style={{ borderRadius: 6, padding: '4px 10px', fontSize: 12, background: 'rgba(255,255,255,0.05)', border: 'none' }}>
                                            {docId}
                                        </Tag>
                                    ))}
                                </Flex>
                            </div>
                        )}

                        <Flex justify="space-between" align="center" style={{ marginTop: 24, padding: '16px 0', borderTop: `1px solid ${token.colorBorderSecondary}` }}>
                            <Space size="large">
                                <Space direction="vertical" size={2}>
                                    <Text type="secondary" style={{ fontSize: 11 }}>Latency</Text>
                                    <Tag color={selectedTrace.latency_ms > 1000 ? 'volcano' : 'green'}>{Math.round(selectedTrace.latency_ms)}ms</Tag>
                                </Space>
                                <Space direction="vertical" size={2}>
                                    <Text type="secondary" style={{ fontSize: 11 }}>Found</Text>
                                    <Tag color="blue">{selectedTrace.total_found} Docs</Tag>
                                </Space>
                                <Space direction="vertical" size={2}>
                                    <Text type="secondary" style={{ fontSize: 11 }}>Prefetch Hit</Text>
                                    <Tag color={selectedTrace.prefetch_hit ? 'success' : 'default'}>{selectedTrace.prefetch_hit ? 'YES' : 'NO'}</Tag>
                                </Space>
                            </Space>
                            <Text type="secondary" style={{ fontSize: 11 }}>Measured at: {new Date(selectedTrace.created_at).toLocaleString()}</Text>
                        </Flex>
                    </Space>
                )}
            </Modal>
        </PageContainer>
    );
};

