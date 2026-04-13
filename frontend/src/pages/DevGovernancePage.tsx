
import React from 'react';
import { Card, Row, Col, Statistic, List, Tag, Progress, Flex, Typography, Alert, Empty } from 'antd';
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
    FileSearchOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

const { Title, Text } = Typography;

export const DevGovernancePage: React.FC = () => {
    const { data: stats, isLoading } = useQuery({
        queryKey: ['dev-governance-stats'],
        queryFn: async () => {
            const res = await api.get('/governance/dev-stats');
            return res.data.data;
        },
        refetchInterval: 10000 
    });

    return (
        <div style={{ padding: 24, background: '#0a0a0a', minHeight: '100%', color: '#fff' }}>
            <Flex vertical gap={24}>
                <Flex align="center" gap={16}>
                    <div style={{ background: 'rgba(24, 144, 255, 0.1)', padding: 12, borderRadius: 12 }}>
                        <SafetyCertificateOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                    </div>
                    <div>
                        <Title level={2} style={{ color: '#fff', margin: 0 }}>研发治理中心</Title>
                        <Text style={{ color: '#8c8c8c' }}>L5 级自主进化治理引擎 · 智体图谱审计观测</Text>
                    </div>
                </Flex>

                <Row gutter={[16, 16]}>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>需求映射覆盖率</Text>}
                                value={stats?.graph_stats?.mapping_coverage || 0}
                                precision={1}
                                valueStyle={{ color: '#06D6A0', fontWeight: 'bold' }}
                                prefix={<PartitionOutlined />}
                                suffix="%"
                            />
                            <Progress 
                                percent={stats?.graph_stats?.mapping_coverage} 
                                showInfo={false} 
                                strokeColor="#06D6A0"
                                trailColor="#262626"
                                style={{ marginTop: 12 }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>图谱架构资产 (Nodes)</Text>}
                                value={stats?.graph_stats?.total_assets || 0}
                                valueStyle={{ color: '#118AB2' }}
                                prefix={<NodeIndexOutlined />}
                            />
                            <Flex gap={8} style={{ marginTop: 12 }}>
                                <Tag color="blue">Agents: {stats?.graph_stats?.node_distribution?.agents || 0}</Tag>
                                <Tag color="cyan">Services: {stats?.graph_stats?.node_distribution?.services || 0}</Tag>
                            </Flex>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>已追踪规约事故</Text>}
                                value={stats?.total_incidents || 0}
                                valueStyle={{ color: '#faad14' }}
                                prefix={<WarningOutlined />}
                            />
                            <Text style={{ color: '#595959', fontSize: 12 }}>最近 24 小时产生</Text>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>代码合规评分</Text>}
                                value={stats?.compliance_score || 0}
                                valueStyle={{ color: '#52c41a' }}
                                prefix={<CheckCircleOutlined />}
                                suffix="%"
                            />
                            <Progress percent={stats?.compliance_score} showInfo={false} strokeColor="#52c41a" trailColor="#262626" style={{ marginTop: 12 }} />
                        </Card>
                    </Col>
                </Row>

                <Row gutter={[16, 16]}>
                    <Col span={10}>
                        <Card 
                            title={<span style={{ color: '#fff' }}><RocketOutlined /> 图谱驱动治理任务 (TODO)</span>}
                            bordered={false} 
                            style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030', height: '100%' }}
                        >
                            <List
                                size="small"
                                dataSource={stats?.todo_stats?.items || []}
                                renderItem={(item: string) => (
                                    <List.Item style={{ borderColor: '#303030' }}>
                                        <Flex gap={8} align="center">
                                            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#1890ff' }} />
                                            <Text style={{ color: '#d9d9d9', fontSize: 13 }}>{item}</Text>
                                        </Flex>
                                    </List.Item>
                                )}
                                locale={{ emptyText: <Empty description="暂无挂起治理任务" /> }}
                            />
                        </Card>
                    </Col>
                    <Col span={14}>
                        <Card 
                            title={<span style={{ color: '#fff' }}><HistoryOutlined /> 架构存根追踪 (Incident Traces)</span>}
                            bordered={false} 
                            style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}
                        >
                            <List
                                dataSource={stats?.recent_incidents || []}
                                renderItem={(incident: any) => (
                                    <List.Item style={{ borderColor: '#303030' }}>
                                        <List.Item.Meta
                                            avatar={<WarningOutlined style={{ color: incident.severity === 'high' ? '#f5222d' : '#faad14', fontSize: 20 }} />}
                                            title={<Text style={{ color: '#fff' }}>{incident.id}</Text>}
                                            description={<Text style={{ color: '#8c8c8c' }}>发现于: {incident.time}</Text>}
                                        />
                                        <Tag color={incident.severity === 'high' ? 'error' : 'warning'}>{incident.severity.toUpperCase()}</Tag>
                                    </List.Item>
                                )}
                                locale={{ emptyText: <Empty description="近期无架构规约事故" /> }}
                            />
                        </Card>
                    </Col>
                </Row>

                <Card 
                    title={<span style={{ color: '#fff' }}><FileSearchOutlined /> 架构智体哨兵 (Architecture Sentinels)</span>}
                    bordered={false} 
                    style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}
                >
                    <Row gutter={[24, 24]}>
                        <Col span={8}>
                            <Flex vertical align="center" gap={12} style={{ background: '#1f1f1f', padding: 20, borderRadius: 12 }}>
                                <SecurityScanOutlined style={{ fontSize: 32, color: '#06D6A0' }} />
                                <Text style={{ color: '#fff' }}>Code-to-Graph Sync</Text>
                                <Tag color="success">STATUS: SYNCHRONIZED</Tag>
                                <Text type="secondary" style={{ fontSize: 11, textAlign: 'center' }}>实时同步文件变更至 Neo4j 架构图谱</Text>
                            </Flex>
                        </Col>
                        <Col span={8}>
                            <Flex vertical align="center" gap={12} style={{ background: '#1f1f1f', padding: 20, borderRadius: 12 }}>
                                <PartitionOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                                <Text style={{ color: '#fff' }}>Semantic Guard</Text>
                                <Tag color="processing">STATUS: ACTIVE</Tag>
                                <Text type="secondary" style={{ fontSize: 11, textAlign: 'center' }}>校验代码实现与需求文档的语义一致性</Text>
                            </Flex>
                        </Col>
                        <Col span={8}>
                            <Flex vertical align="center" gap={12} style={{ background: '#1f1f1f', padding: 20, borderRadius: 12 }}>
                                <BugOutlined style={{ fontSize: 32, color: '#faad14' }} />
                                <Text style={{ color: '#fff' }}>Trace Oracle</Text>
                                <Tag color="warning">STATUS: MONITORING</Tag>
                                <Text type="secondary" style={{ fontSize: 11, textAlign: 'center' }}>全链路监控跨服务调用链路的健康度</Text>
                            </Flex>
                        </Col>
                    </Row>
                </Card>
            </Flex>
        </div>
    );
};
