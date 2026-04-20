
/**
 * Agent Governance Page - Cognitive Directives Audit & Red Team Campaign monitoring.
 * 
 * @covers REQ-007
 */
import React, { useState } from 'react';
import { Card, Row, Col, Statistic, List, Tag, Flex, Typography, Badge, Descriptions, Empty, Space, Button, Tabs, Table, message, Progress, Skeleton } from 'antd';
import { 
    BulbOutlined, 
    RocketOutlined, 
    SecurityScanOutlined, 
    BugOutlined,
    SafetyCertificateOutlined,
    DashboardOutlined,
    SyncOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    ThunderboltOutlined,
    HistoryOutlined,
    EyeOutlined,
    AlertOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

const { Title, Text } = Typography;

export const AgentGovernancePage: React.FC = () => {
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState('evolution');

    // 1. Fetch Governance Summary
    const { data: summary, isLoading: isSummaryLoading } = useQuery({
        queryKey: ['agent-governance-summary'],
        queryFn: async () => {
            const res = await api.get('/evaluation/governance/summary');
            return res.data.data;
        },
        refetchInterval: 15000 
    });

    // 2. Fetch All Directives
    const { data: directives } = useQuery({
        queryKey: ['agent-directives'],
        queryFn: async () => {
            const res = await api.get('/evaluation/directives');
            return res.data.data;
        }
    });

    // 3. Red Team History
    const { data: rtHistory, isLoading: isRtLoading } = useQuery({
        queryKey: ['red-team-history'],
        queryFn: async () => {
            const res = await api.get('/red-team/campaign/history');
            return res.data.data;
        },
        enabled: activeTab === 'red-team'
    });

    // 4. Trigger Campaign
    const runCampaign = useMutation({
        mutationFn: async () => {
            const res = await api.post('/red-team/campaign/run', { scenarios: null });
            return res.data;
        },
        onSuccess: () => {
            message.success('红队压测已在后台启动，请稍后查看报告');
            queryClient.invalidateQueries({ queryKey: ['red-team-history'] });
        }
    });

    // 5. Audit Directive
    const auditDirective = useMutation({
        mutationFn: async ({ id, status }: { id: string, status: string }) => {
            const res = await api.put(`/evaluation/directives/${id}`, { status });
            return res.data;
        },
        onSuccess: () => {
            message.success('指令已成功更新');
            queryClient.invalidateQueries({ queryKey: ['agent-directives'] });
            queryClient.invalidateQueries({ queryKey: ['agent-governance-summary'] });
        },
        onError: (err: any) => {
            message.error(`更新失败: ${err.message || '未知错误'}`);
        }
    });

    // 6. Fetch Governance Gates
    const { data: gatesData, isLoading: isGatesLoading } = useQuery({
        queryKey: ['agent-governance-gates'],
        queryFn: async () => {
            const res = await api.get('/evaluation/governance/gates');
            return res.data.data;
        },
        refetchInterval: 30000
    });

    const rtColumns = [
        {
            title: 'Campaign ID',
            dataIndex: 'id',
            key: 'id',
            render: (text: string) => <Text style={{ color: '#06D6A0' }}>{text}</Text>
        },
        {
            title: '测试时间',
            dataIndex: 'timestamp',
            key: 'timestamp',
            render: (text: string) => <Text style={{ color: '#94a3b8' }}>{new Date(text).toLocaleString()}</Text>
        },
        {
            title: '场景总数',
            dataIndex: 'total_scenarios',
            key: 'total_scenarios',
            align: 'center' as const
        },
        {
            title: '拦截率 (Detection Rate)',
            dataIndex: 'detection_rate',
            key: 'detection_rate',
            render: (rate: number) => (
                <Flex align="center" gap={8}>
                    <Progress 
                        percent={rate * 100} 
                        size="small" 
                        strokeColor={rate > 0.8 ? '#06D6A0' : (rate > 0.5 ? '#ffd166' : '#EF476F')} 
                        showInfo={false}
                        style={{ width: 100 }}
                    />
                    <Text style={{ color: rate > 0.8 ? '#06D6A0' : '#EF476F' }}>{(rate * 100).toFixed(1)}%</Text>
                </Flex>
            )
        },
        {
            title: '操作',
            key: 'action',
            render: () => (
                <Button size="small" ghost icon={<EyeOutlined />}>详情</Button>
            )
        }
    ];

    const renderGates = () => {
        if (isGatesLoading || !gatesData) return <Skeleton active />;
        const gates = gatesData.gates;
        
        return (
            <Row gutter={[24, 24]}>
                {Object.entries(gates).map(([id, gate]: [string, any]) => (
                    <Col xs={24} md={12} key={id}>
                        <Card 
                            style={{ 
                                background: '#111827', 
                                border: `1px solid ${gate.passed ? 'rgba(6, 214, 160, 0.2)' : 'rgba(239, 71, 111, 0.2)'}`,
                                borderRadius: 16 
                            }}
                            title={<span style={{ color: '#fff' }}>{id}: {gate.name}</span>}
                            extra={
                                <Tag color={gate.passed ? 'success' : 'error'} icon={gate.passed ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
                                    {gate.passed ? 'PASSED' : 'FAILED'}
                                </Tag>
                            }
                        >
                            <Flex vertical gap={12}>
                                {gate.status === 'unknown' ? (
                                    <Empty description="未检测到报告，请运行验证脚本" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                                ) : (
                                    <>
                                        {id === 'SG1' && (
                                            <Descriptions column={1} size="small" labelStyle={{ color: '#94a3b8' }} contentStyle={{ color: '#f8fafc' }}>
                                                <Descriptions.Item label="均值稳定性">{( (1 - gate.details.global_error_budget) * 100).toFixed(1)}%</Descriptions.Item>
                                                <Descriptions.Item label="Steady Block Rate">{(gate.details.steady_block_ratio * 100).toFixed(2)}%</Descriptions.Item>
                                                <Descriptions.Item label="样本总数">{gate.details.global_total_requests}</Descriptions.Item>
                                            </Descriptions>
                                        )}
                                        {id === 'SG2' && (
                                            <div style={{ maxHeight: 100, overflow: 'auto' }}>
                                                {(gate.details.results || []).map((r: any) => (
                                                    <Tag key={r.dependency} color={r.success ? 'cyan' : 'red'} style={{ marginBottom: 4 }}>
                                                        {r.dependency}: {r.success ? 'Resilient' : 'Fail'}
                                                    </Tag>
                                                ))}
                                            </div>
                                        )}
                                        {id === 'SG3' && (
                                            <Descriptions column={1} size="small" labelStyle={{ color: '#94a3b8' }} contentStyle={{ color: '#f8fafc' }}>
                                                <Descriptions.Item label="Cost Reduction">{(gate.details.cost_reduction_ratio * 100).toFixed(1)}%</Descriptions.Item>
                                                <Descriptions.Item label="Quality Delta">{(gate.details.quality_delta * 100).toFixed(2)}%</Descriptions.Item>
                                            </Descriptions>
                                        )}
                                        {id === 'SG4' && (
                                            <Flex wrap="wrap" gap={8}>
                                                {Object.entries(gate.details).map(([k, v]: [string, any]) => (
                                                    <Badge key={k} status={v ? 'success' : 'error'} text={<span style={{ color: v ? '#06D6A0' : '#EF476F', fontSize: 12 }}>{k}</span>} />
                                                ))}
                                            </Flex>
                                        )}
                                    </>
                                )}
                            </Flex>
                        </Card>
                    </Col>
                ))}
            </Row>
        );
    };

    return (
        <div style={{ padding: 24, background: '#0a0e1a', minHeight: '100%', color: '#fff' }}>
            <Flex vertical gap={24}>
                {/* Header Section */}
                <Flex align="center" justify="space-between">
                    <Flex align="center" gap={16}>
                        <div style={{ 
                            background: 'linear-gradient(135deg, rgba(6, 214, 160, 0.2) 0%, rgba(17, 138, 178, 0.2) 100%)', 
                            padding: 12, 
                            borderRadius: 16,
                            boxShadow: '0 4px 20px rgba(6, 214, 160, 0.1)'
                        }}>
                            <BulbOutlined style={{ fontSize: 32, color: '#06D6A0' }} />
                        </div>
                        <div>
                            <Title level={2} style={{ color: '#fff', margin: 0 }}>智灵治理中心 (Agent Governance)</Title>
                            <Text style={{ color: '#94a3b8' }}>
                                L5 智体自主进化引擎 · 认知铁律治理 · 对抗性安全压测
                            </Text>
                        </div>
                    </Flex>
                    <Space>
                        <Badge status="processing" text={<Text style={{ color: gatesData?.overall_status === 'READY_ FOR_PROD' ? '#06D6A0' : '#ffd166' }}>系统状态: {gatesData?.overall_status || 'Checking...'}</Text>} />
                        <Button 
                            type="primary" 
                            danger 
                            icon={<ThunderboltOutlined />} 
                            onClick={() => runCampaign.mutate()}
                            loading={runCampaign.isPending}
                        >
                            启动红队压测
                        </Button>
                    </Space>
                </Flex>

                <Tabs 
                    activeKey={activeTab} 
                    onChange={setActiveTab}
                    items={[
                        {
                            key: 'evolution',
                            label: <span style={{ color: activeTab === 'evolution' ? '#06D6A0' : '#94a3b8' }}><RocketOutlined /> 自主进化</span>,
                            children: (
                                <Flex vertical gap={24}>
                                    {/* Hero Metrics */}
                                    <Row gutter={[24, 24]}>
                                        <Col xs={24} sm={12} md={6}>
                                            <Card bordered={false} style={{ background: '#111827', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)' }}>
                                                <Statistic
                                                    title={<Text style={{ color: '#94a3b8' }}>L3 智商评分 (Avg)</Text>}
                                                    value={summary?.l3_avg_score || 0}
                                                    precision={2}
                                                    valueStyle={{ color: '#06D6A0', fontWeight: 'bold', fontSize: 28 }}
                                                    prefix={<DashboardOutlined />}
                                                />
                                            </Card>
                                        </Col>
                                        <Col xs={24} sm={12} md={6}>
                                            <Card bordered={false} style={{ background: '#111827', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)' }}>
                                                <Statistic
                                                    title={<Text style={{ color: '#94a3b8' }}>已提炼认知铁律</Text>}
                                                    value={summary?.active_directives_count || 0}
                                                    valueStyle={{ color: '#118AB2' }}
                                                    prefix={<SafetyCertificateOutlined />}
                                                />
                                            </Card>
                                        </Col>
                                        <Col xs={24} sm={12} md={6}>
                                            <Card bordered={false} style={{ background: '#111827', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)' }}>
                                                <Statistic
                                                    title={<Text style={{ color: '#94a3b8' }}>拦截攻击次数</Text>}
                                                    value={12}
                                                    valueStyle={{ color: '#EF476F' }}
                                                    prefix={<AlertOutlined />}
                                                />
                                            </Card>
                                        </Col>
                                        <Col xs={24} sm={12} md={6}>
                                            <Card bordered={false} style={{ background: '#111827', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)' }}>
                                                <Statistic
                                                    title={<Text style={{ color: '#94a3b8' }}>防御健壮度</Text>}
                                                    value={94.2}
                                                    suffix="%"
                                                    valueStyle={{ color: '#118AB2' }}
                                                    prefix={<SecurityScanOutlined />}
                                                />
                                            </Card>
                                        </Col>
                                    </Row>

                                    <Row gutter={[24, 24]}>
                                        <Col span={16}>
                                            <Card 
                                                title={<span style={{ color: '#fff' }}><SecurityScanOutlined /> 进化铁律审计 (Cognitive Directives Audit)</span>}
                                                bordered={false} 
                                                style={{ background: '#111827', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)', minHeight: 400 }}
                                                extra={<Text style={{ color: '#94a3b8' }}>共 {directives?.length || 0} 条</Text>}
                                            >
                                                <List
                                                    dataSource={directives || []}
                                                    renderItem={(cd: any) => (
                                                        <List.Item style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                                                            <Card style={{ 
                                                                width: '100%', 
                                                                background: cd.status === 'pending' ? 'rgba(255, 209, 102, 0.05)' : 'rgba(255,255,255,0.02)', 
                                                                border: cd.status === 'pending' ? '1px solid rgba(255, 209, 102, 0.2)' : 'none',
                                                                borderRadius: 12
                                                            }}>
                                                                <Flex vertical gap={12}>
                                                                    <Flex justify="space-between" align="start">
                                                                        <div style={{ flex: 1 }}>
                                                                            <Flex align="center" gap={8} style={{ marginBottom: 8 }}>
                                                                                <Tag color="cyan">{cd.topic}</Tag>
                                                                                {cd.status === 'pending' && <Badge status="warning" text={<Text style={{ color: '#ffd166' }}>待审核</Text>} />}
                                                                                {cd.status === 'approved' && <Badge status="success" text={<Text style={{ color: '#06D6A0' }}>已生效</Text>} />}
                                                                                {cd.status === 'rejected' && <Badge status="error" text={<Text style={{ color: '#EF476F' }}>已驳回</Text>} />}
                                                                            </Flex>
                                                                            <Text style={{ color: '#f8fafc', fontSize: 16, display: 'block', marginBottom: 8 }}>
                                                                                {cd.directive}
                                                                            </Text>
                                                                            <Text style={{ color: '#64748b', fontSize: 12 }}>
                                                                                提炼时间: {new Date(cd.created_at).toLocaleString()} | 置信度: {(cd.confidence_score * 100).toFixed(1)}%
                                                                            </Text>
                                                                        </div>
                                                                        <Flex vertical align="end" gap={8}>
                                                                            <Statistic value={cd.confidence_score * 100} suffix="%" valueStyle={{ color: '#06D6A0', fontSize: 18 }} />
                                                                        </Flex>
                                                                    </Flex>
                                                                    
                                                                    {cd.status === 'pending' && (
                                                                        <Flex gap={12} justify="end" style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
                                                                            <Button 
                                                                                danger 
                                                                                size="small" 
                                                                                onClick={() => auditDirective.mutate({ id: cd.id, status: 'rejected' })}
                                                                                loading={auditDirective.isPending}
                                                                            >
                                                                                驳回
                                                                            </Button>
                                                                            <Button 
                                                                                type="primary" 
                                                                                size="small" 
                                                                                style={{ background: '#06D6A0', borderColor: '#06D6A0' }}
                                                                                onClick={() => auditDirective.mutate({ id: cd.id, status: 'approved' })}
                                                                                loading={auditDirective.isPending}
                                                                            >
                                                                                批准并发布
                                                                            </Button>
                                                                        </Flex>
                                                                    )}
                                                                </Flex>
                                                            </Card>
                                                        </List.Item>
                                                    )}
                                                    locale={{ emptyText: <Empty description={<span style={{ color: '#94a3b8' }}>暂无进化指令，请先运行 RAG 评测以自动捕获模式</span>} /> }}
                                                />
                                            </Card>
                                        </Col>
                                        <Col span={8}>
                                            <Card title={<span style={{ color: '#fff' }}><SyncOutlined /> 实时反馈流</span>} bordered={false} style={{ background: '#111827', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)' }}>
                                                <Empty description="等候 BadCase 反馈" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                                            </Card>
                                        </Col>
                                    </Row>
                                </Flex>
                            )
                        },
                        {
                            key: 'gates',
                            label: <span style={{ color: activeTab === 'gates' ? '#06D6A0' : '#94a3b8' }}><SafetyCertificateOutlined /> 治理门禁 (Gates)</span>,
                            children: renderGates()
                        },
                        {
                            key: 'red-team',
                            label: <span style={{ color: activeTab === 'red-team' ? '#EF476F' : '#94a3b8' }}><SecurityScanOutlined /> 对抗性测试 (Red Team)</span>,
                            children: (
                                <Card 
                                    title={<span style={{ color: '#fff' }}><HistoryOutlined /> 压测历史报告 (Campaign History)</span>}
                                    bordered={false} 
                                    style={{ background: '#111827', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)' }}
                                >
                                    <Table 
                                        columns={rtColumns} 
                                        dataSource={rtHistory || []} 
                                        loading={isRtLoading}
                                        rowKey="id"
                                        pagination={{ pageSize: 10 }}
                                        style={{ background: 'transparent' }}
                                        className="dark-table"
                                    />
                                </Card>
                            )
                        }
                    ]}
                />
            </Flex>
        </div>
    );
};
