
import React from 'react';
import { Card, Row, Col, Statistic, List, Tag, Progress, Flex, Typography, Alert, Empty, Button } from 'antd';
import { 
    SafetyCertificateOutlined, 
    HistoryOutlined, 
    CheckCircleOutlined, 
    WarningOutlined,
    RocketOutlined,
    SecurityScanOutlined,
    BugOutlined,
    NodeIndexOutlined,
    PartitionOutlined,
    FileSearchOutlined,
    DatabaseOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';

const { Title, Text } = Typography;

export const DevGovernancePage: React.FC = () => {
    const navigate = useNavigate();
    const { data: stats, isLoading } = useQuery({
        queryKey: ['dev-governance-stats'],
        queryFn: async () => {
            const res = await api.get('/governance/dev-stats');
            return res.data.data;
        },
        refetchInterval: 10000 
    });

    const isMappingZero = stats?.graph_stats?.mapping_coverage === 0;

    return (
        <div style={{ padding: 24, background: 'var(--hm-color-bg-deepest)', minHeight: '100%', color: 'var(--hm-color-text-primary)' }}>
            <Flex vertical gap={24}>
                <Flex align="center" gap={16}>
                    <div style={{ background: 'rgba(17, 138, 178, 0.1)', padding: 12, borderRadius: 12 }}>
                        <SafetyCertificateOutlined style={{ fontSize: 32, color: 'var(--hm-color-info)' }} />
                    </div>
                    <div>
                        <Title level={2} style={{ color: 'var(--hm-color-text-primary)', margin: 0 }}>研发治理中心</Title>
                        <Text style={{ color: 'var(--hm-color-text-secondary)' }}>L5 级自主进化治理引擎 · 全链路架构资产探测</Text>
                    </div>
                </Flex>

                {isMappingZero && (
                    <Alert
                        message="架构审计警告 (Architecture Drift)"
                        description="检测到需求映射率为 0.0%。图谱中存在需求与设计节点，但尚未建立跨越到代码实现 (File/CodeEntity) 的 IMPLEMENTED_BY 语义链路。建议启动‘智体同步’任务补齐映射。"
                        type="warning"
                        showIcon
                        icon={<PartitionOutlined />}
                        style={{ background: 'rgba(255, 209, 102, 0.1)', border: '1px solid var(--hm-color-warning)', color: 'var(--hm-color-warning)' }}
                    />
                )}

                <Row gutter={[16, 16]}>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)' }}>
                            <Statistic
                                title={<Text style={{ color: 'var(--hm-color-text-secondary)' }}>需求映射覆盖率</Text>}
                                value={stats?.graph_stats?.mapping_coverage || 0}
                                precision={1}
                                valueStyle={{ color: isMappingZero ? 'var(--hm-color-danger)' : 'var(--hm-color-brand)', fontWeight: 'bold' }}
                                prefix={<PartitionOutlined />}
                                suffix="%"
                            />
                            <Progress 
                                percent={stats?.graph_stats?.mapping_coverage} 
                                showInfo={false} 
                                strokeColor={isMappingZero ? 'var(--hm-color-danger)' : 'var(--hm-color-brand)'}
                                trailColor="var(--hm-color-bg-elevated)"
                                style={{ marginTop: 12 }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)' }}>
                            <Statistic
                                title={<Text style={{ color: 'var(--hm-color-text-secondary)' }}>图谱架构资产 (Nodes)</Text>}
                                value={stats?.graph_stats?.total_assets || 0}
                                valueStyle={{ color: 'var(--hm-color-accent)' }}
                                prefix={<NodeIndexOutlined />}
                            />
                            <Flex gap={8} style={{ marginTop: 12 }}>
                                <Tag color="blue">Logic: {stats?.graph_stats?.node_distribution?.logic_entities || 0}</Tag>
                                <Tag color="cyan">Design: {stats?.graph_stats?.node_distribution?.design_docs || 0}</Tag>
                            </Flex>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)' }}>
                            <Statistic
                                title={<Text style={{ color: 'var(--hm-color-text-secondary)' }}>已拦截事故 (Recent)</Text>}
                                value={stats?.total_incidents || 0}
                                valueStyle={{ color: 'var(--hm-color-warning)' }}
                                prefix={<WarningOutlined />}
                            />
                            <Text style={{ color: 'var(--hm-color-text-muted)', fontSize: 12 }}>合规防御机制已生效</Text>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)' }}>
                            <Statistic
                                title={<Text style={{ color: 'var(--hm-color-text-secondary)' }}>治理体系版本</Text>}
                                value="L5.2"
                                valueStyle={{ color: 'var(--hm-color-info)' }}
                                prefix={<RocketOutlined />}
                            />
                            <Text style={{ color: 'var(--hm-color-text-muted)', fontSize: 12 }}>自省引擎: Active</Text>
                        </Card>
                    </Col>
                </Row>

                <Row gutter={[16, 16]}>
                    <Col span={8}>
                        <Card 
                            title={<span style={{ color: 'var(--hm-color-text-primary)' }}><RocketOutlined /> 治理待办 (TODO)</span>}
                            bordered={false} 
                            style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)', height: '100%' }}
                        >
                            <List
                                size="small"
                                dataSource={stats?.todo_stats?.items || []}
                                renderItem={(item: string) => (
                                    <List.Item style={{ borderColor: 'var(--hm-color-bg-elevated)', padding: '8px 0' }}>
                                        <div className="governance-todo-item" style={{ color: 'var(--hm-color-text-secondary)', fontSize: 12, width: '100%' }}>
                                            <ReactMarkdown
                                                components={{
                                                    p: ({ node, ...props }) => <p style={{ margin: 0 }} {...props} />,
                                                    strong: ({ node, ...props }) => <strong style={{ color: 'var(--hm-color-warning)' }} {...props} />
                                                }}
                                            >
                                                {item}
                                            </ReactMarkdown>
                                        </div>
                                    </List.Item>
                                )}
                            />
                        </Card>
                    </Col>
                    <Col span={8}>
                        <Card 
                            title={<span style={{ color: 'var(--hm-color-text-primary)' }}><DatabaseOutlined /> 资产发现流水 (Asset Feed)</span>}
                            extra={<Button type="link" size="small" onClick={() => navigate('/governance/assets')}>查看全部</Button>}
                            bordered={false} 
                            style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)', height: '100%' }}
                        >
                            <List
                                size="small"
                                dataSource={stats?.graph_stats?.recent_assets || []}
                                renderItem={(assetDetail: any) => (
                                    <List.Item style={{ borderColor: 'var(--hm-color-bg-elevated)' }}>
                                        <Flex vertical>
                                            <Text style={{ color: 'var(--hm-color-text-primary)', fontSize: 12 }}>{assetDetail.name}</Text>
                                            <Tag color="geekblue" style={{ fontSize: 10, alignSelf: 'start', marginTop: 4 }}>{assetDetail.type}</Tag>
                                        </Flex>
                                    </List.Item>
                                )}
                            />
                        </Card>
                    </Col>
                    <Col span={8}>
                        <Card 
                            title={<span style={{ color: 'var(--hm-color-text-primary)' }}><HistoryOutlined /> 事故追踪 (Incidents)</span>}
                            bordered={false} 
                            style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)', height: '100%' }}
                        >
                            <List
                                size="small"
                                dataSource={stats?.recent_incidents || []}
                                renderItem={(incident: any) => (
                                    <List.Item style={{ borderColor: 'var(--hm-color-bg-elevated)' }}>
                                        <Flex vertical style={{ width: '100%' }}>
                                            <Flex justify="space-between">
                                                <Text style={{ color: 'var(--hm-color-text-primary)', fontSize: 12 }} ellipsis>{incident.id}</Text>
                                                <Tag color={incident.severity === 'high' ? 'error' : 'warning'} style={{ fontSize: 10 }}>{incident.severity}</Tag>
                                            </Flex>
                                            <Text style={{ color: 'var(--hm-color-text-muted)', fontSize: 10 }}>{incident.time}</Text>
                                        </Flex>
                                    </List.Item>
                                )}
                            />
                        </Card>
                    </Col>
                </Row>

                <Card 
                    title={<span style={{ color: 'var(--hm-color-text-primary)' }}><FileSearchOutlined /> 治理哨兵状态 (Sentinels)</span>}
                    bordered={false} 
                    style={{ background: 'var(--hm-color-bg-base)', borderRadius: 12, border: 'var(--hm-border-light)' }}
                >
                    <Row gutter={[16, 16]}>
                        <Col span={8}>
                            <Flex gap={12} align="center" style={{ background: 'var(--hm-color-bg-float)', padding: '12px 16px', borderRadius: 8 }}>
                                <SecurityScanOutlined style={{ fontSize: 24, color: stats?.guard_status?.sync_sentinel === 'healthy' ? 'var(--hm-color-brand)' : 'var(--hm-color-warning)' }} />
                                <div style={{ flex: 1 }}>
                                    <Text style={{ color: 'var(--hm-color-text-primary)', fontSize: 13, display: 'block' }}>SyncSentinel</Text>
                                    <Text type="secondary" style={{ fontSize: 11 }}>
                                        {stats?.guard_status?.sync_sentinel === 'healthy' ? '图谱资产同步正常' : `检测到 ${stats?.graph_stats?.islands || 0} 个孤岛节点`}
                                    </Text>
                                </div>
                                <Tag color={stats?.guard_status?.sync_sentinel === 'healthy' ? 'success' : 'warning'}>
                                    {stats?.guard_status?.sync_sentinel === 'healthy' ? 'OK' : 'WARN'}
                                </Tag>
                            </Flex>
                        </Col>
                        <Col span={8}>
                            <Flex gap={12} align="center" style={{ background: 'var(--hm-color-bg-float)', padding: '12px 16px', borderRadius: 8 }}>
                                <PartitionOutlined style={{ fontSize: 24, color: stats?.guard_status?.mapping_guard === 'active' ? 'var(--hm-color-info)' : 'var(--hm-color-warning)' }} />
                                <div style={{ flex: 1 }}>
                                    <Text style={{ color: 'var(--hm-color-text-primary)', fontSize: 13, display: 'block' }}>MappingGuard</Text>
                                    <Text type="secondary" style={{ fontSize: 11 }}>
                                        {stats?.guard_status?.mapping_guard === 'active' ? '全链路映射已对齐' : '检测到语义链路缺失'}
                                    </Text>
                                </div>
                                <Tag color={stats?.guard_status?.mapping_guard === 'active' ? "success" : "warning"}>
                                    {stats?.guard_status?.mapping_guard === 'active' ? "SYNC" : "DRFT"}
                                </Tag>
                            </Flex>
                        </Col>
                        <Col span={8}>
                            <Flex gap={12} align="center" style={{ background: 'var(--hm-color-bg-float)', padding: '12px 16px', borderRadius: 8 }}>
                                <BugOutlined style={{ fontSize: 24, color: 'var(--hm-color-warning)' }} />
                                <div style={{ flex: 1 }}>
                                    <Text style={{ color: 'var(--hm-color-text-primary)', fontSize: 13, display: 'block' }}>TraceOracle</Text>
                                    <Text type="secondary" style={{ fontSize: 11 }}>
                                        {stats?.guard_status?.trace_oracle === 'armed' ? '正在监控核心链路' : '审计引擎离线'}
                                    </Text>
                                </div>
                                <Tag color={stats?.guard_status?.trace_oracle === 'armed' ? "processing" : "default"}>
                                    {stats?.guard_status?.trace_oracle === 'armed' ? "RUN" : "OFF"}
                                </Tag>
                            </Flex>
                        </Col>
                    </Row>
                </Card>
            </Flex>
        </div>
    );
};
