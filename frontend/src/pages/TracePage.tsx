import React, { useState } from 'react';
import { Table, Tag, Card, Typography, Modal, Space, Timeline, Badge, Flex, theme, Button } from 'antd';
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
    RocketOutlined
} from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { useTraces } from '../hooks/queries/useDashboardQuery';

const { Text, Title, Paragraph } = Typography;

// Mapping pipe steps to icons and colors - Using semantic generic strings for now to avoid hex
const STEP_CONFIG: Record<string, { icon: React.ReactNode, color: string, label: string }> = {
    "QueryPreProcessingStep": { icon: <RetweetOutlined />, color: 'var(--hm-color-brand)', label: '查询改写' },
    "GraphRetrievalStep": { icon: <NodeIndexOutlined />, color: 'var(--hm-color-purple)', label: '知识图谱检索' },
    "SqlSummaryFirstStep": { icon: <FileSearchOutlined />, color: 'var(--hm-color-pink)', label: 'SQL 摘要检索' },
    "SearchSubagentsStep": { icon: <RocketOutlined />, color: 'var(--hm-color-orange)', label: '子代理并行检索' },
    "RRFHybridStep": { icon: <ExperimentOutlined />, color: 'var(--hm-color-blue)', label: 'RRF 混合检索' },
    "TruthAlignmentStep": { icon: <SafetyCertificateOutlined />, color: 'var(--hm-color-success)', label: '真相对齐' },
    "AclFilterStep": { icon: <BugOutlined />, color: 'var(--hm-color-warning)', label: 'ACL 权限过滤' },
    "RerankingStep": { icon: <ThunderboltOutlined />, color: 'var(--hm-color-gold)', label: '交叉编码重排' },
    "ParentChunkExpansionStep": { icon: <SearchOutlined />, color: 'var(--hm-color-cyan)', label: '父分片扩展' },
    "ContextualCompressionStep": { icon: <CompressOutlined />, color: 'var(--hm-color-volcano)', label: '上下文压缩' },
    "PromptInjectionFilterStep": { icon: <SafetyCertificateOutlined />, color: 'var(--hm-color-error)', label: '安全注入防御' },
    "Pipeline": { icon: <CheckCircleOutlined />, color: 'var(--hm-color-text-quaternary)', label: '管道流水线' }
};

import { useMonitor } from '../hooks/useMonitor';

export const TracePage: React.FC = () => {
    const { track } = useMonitor();

    React.useEffect(() => {
        track('system', 'page_load', { page: 'TraceViewer' });
    }, [track]);

    const { token } = theme.useToken();
    const { data: traces, isLoading: isLoadingTraces } = useTraces();
    const [selectedTrace, setSelectedTrace] = useState<any>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);

    const columns = [
        {
            title: '时间',
            dataIndex: 'created_at',
            key: 'time',
            render: (t: string) => new Date(t).toLocaleTimeString(),
            width: 100
        },
        {
            title: '问题 (Query)',
            dataIndex: 'query',
            key: 'query',
            ellipsis: true,
            render: (text: string) => <Text strong>{text}</Text>
        },
        {
            title: '策略',
            dataIndex: 'retrieval_strategy',
            key: 'strategy',
            render: (s: string) => <Tag color="blue">{s.toUpperCase()}</Tag>,
            width: 120
        },
        {
            title: '召回数',
            dataIndex: 'total_found',
            key: 'found',
            align: 'center' as const,
            render: (n: number) => <Badge count={n} showZero color={n > 0 ? token.colorSuccess : token.colorError} />
        },
        {
            title: '延迟',
            dataIndex: 'latency_ms',
            key: 'latency',
            render: (ms: number) => <Tag icon={<ClockCircleOutlined />} color={ms > 500 ? 'orange' : 'green'}>{Math.round(ms)}ms</Tag>,
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
                    全链路详情
                </Button>
            ),
            width: 120
        }
    ];

    const parseStepTraces = (tracesArray: string[]) => {
        if (!tracesArray || tracesArray.length === 0) return [];

        return tracesArray.map(log => {
            // Log format: "[StepName] status=... msg=..."
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

    return (
        <PageContainer
            title="V3 Trace 全链路可视化 (M5.2.3)"
            description="深度透视 RAG 检索流水线：从 Query 改写到 Rerank 压缩的完整决策链条。"
        >
            <Card bordered={false} styles={{ body: { padding: 0 } }} style={{ borderRadius: 16, overflow: 'hidden' }}>
                <Table
                    dataSource={(traces as any)?.data || []}
                    columns={columns}
                    rowKey="id"
                    loading={isLoadingTraces}
                    pagination={{ pageSize: 12 }}
                />
            </Card>

            <Modal
                title={
                    <Flex align="center" gap={8}>
                        <NodeIndexOutlined />
                        <span>RAG 意识流全链路追踪 — ID: {selectedTrace?.id.slice(0, 8)}</span>
                    </Flex>
                }
                open={isDetailOpen}
                onCancel={() => setIsDetailOpen(false)}
                footer={null}
                width={800}
                styles={{ body: { padding: '24px' } }}
            >
                {selectedTrace && (
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        <div style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.05)' }}>
                            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>用户原始提问</Text>
                            <Title level={4} style={{ margin: 0, color: token.colorPrimary }}>{selectedTrace.query}</Title>
                        </div>

                        <Timeline
                            mode="left"
                            items={parseStepTraces(selectedTrace.step_traces).map((step, idx) => ({
                                color: step.config.color,
                                label: <Text type="secondary" style={{ fontSize: 11 }}>Phase {idx + 1}</Text>,
                                children: (
                                    <div style={{ marginBottom: 16 }}>
                                        <Flex align="center" gap={8} style={{ marginBottom: 4 }}>
                                            <span style={{ 
                                                display: 'inline-flex', 
                                                padding: '4px', 
                                                borderRadius: '6px', 
                                                background: `${step.config.color}22`, 
                                                color: step.config.color 
                                            }}>
                                                {step.config.icon}
                                            </span>
                                            <Text strong>{step.config.label}</Text>
                                            <Text type="secondary" style={{ fontSize: 12 }}>{step.name}</Text>
                                        </Flex>
                                        <Card size="small" style={{ borderRadius: 8, background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)' }}>
                                            <Paragraph style={{ margin: 0, fontSize: 13, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                                                {step.content}
                                            </Paragraph>
                                        </Card>
                                    </div>
                                ),
                                dot: <div style={{ 
                                    width: 12, height: 12, borderRadius: '50%', 
                                    background: step.config.color,
                                    boxShadow: `0 0 10px ${step.config.color}`
                                }} />
                            }))}
                        />

                        {selectedTrace.retrieved_doc_ids?.length > 0 && (
                            <div style={{ marginTop: 8 }}>
                                <Title level={5}><FileSearchOutlined /> 最终检索命中文档</Title>
                                <Flex wrap="wrap" gap={8}>
                                    {selectedTrace.retrieved_doc_ids.map((docId: string) => (
                                        <Tag key={docId} color="default" style={{ borderRadius: 4 }}>{docId}</Tag>
                                    ))}
                                </Flex>
                            </div>
                        )}

                        <Flex justify="space-between" align="center" style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                            <Space>
                                <Tag color="gold">Cost Estimate: Pending</Tag>
                                <Tag color="cyan">Quality Check: OK</Tag>
                            </Space>
                            <Text type="secondary" style={{ fontSize: 12 }}>Time: {new Date(selectedTrace.created_at).toLocaleString()}</Text>
                        </Flex>
                    </Space>
                )}
            </Modal>
        </PageContainer>
    );
};
