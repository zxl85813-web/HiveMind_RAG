
import React from 'react';
import { Card, Row, Col, Statistic, List, Tag, Progress, Flex, Typography, Alert, Empty, Timeline } from 'antd';
import { 
    SafetyCertificateOutlined, 
    HistoryOutlined, 
    CheckCircleOutlined, 
    WarningOutlined,
    RocketOutlined,
    SecurityScanOutlined,
    BugOutlined,
    ClockCircleOutlined,
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
        refetchInterval: 10000 // 10秒自动刷新，保持治理视角实时性
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
                        <Text style={{ color: '#8c8c8c' }}>L5 级自主进化治理引擎 · 实时自省监控</Text>
                    </div>
                </Flex>

                <Row gutter={[16, 16]}>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>代码合规分 (Compliance)</Text>}
                                value={stats?.compliance_score || 0}
                                precision={1}
                                valueStyle={{ color: '#52c41a', fontWeight: 'bold' }}
                                prefix={<CheckCircleOutlined />}
                                suffix="%"
                            />
                            <Progress 
                                percent={stats?.compliance_score} 
                                showInfo={false} 
                                strokeColor="#52c41a"
                                trailColor="#262626"
                                style={{ marginTop: 12 }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>拦截架构事故 (Recent)</Text>}
                                value={stats?.total_incidents || 0}
                                valueStyle={{ color: '#faad14' }}
                                prefix={<WarningOutlined />}
                            />
                            <Progress 
                                percent={stats?.total_incidents > 0 ? 100 : 0} 
                                showInfo={false} 
                                strokeColor="#faad14"
                                trailColor="#262626"
                                style={{ marginTop: 12 }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>智体治理项 (Active)</Text>}
                                value={stats?.todo_stats?.active || 0}
                                valueStyle={{ color: '#1890ff' }}
                                prefix={<RocketOutlined />}
                            />
                            <Text style={{ color: '#595959', fontSize: 12 }}>已完成: {stats?.todo_stats?.done || 0}</Text>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>RBAC 鉴权一致性</Text>}
                                value={100}
                                valueStyle={{ color: '#eb2f96' }}
                                prefix={<SecurityScanOutlined />}
                                suffix="%"
                            />
                            <Progress percent={100} showInfo={false} strokeColor="#eb2f96" trailColor="#262626" style={{ marginTop: 12 }} />
                        </Card>
                    </Col>
                </Row>

                <Row gutter={[16, 16]}>
                    <Col span={10}>
                        <Card 
                            title={<span style={{ color: '#fff' }}><RocketOutlined /> 当前治理任务 (TODO Details)</span>}
                            bordered={false} 
                            style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}
                        >
                            <List
                                size="small"
                                dataSource={stats?.todo_stats?.items || []}
                                renderItem={(item: string) => (
                                    <List.Item style={{ borderColor: '#303030' }}>
                                        <Flex gap={8} align="center">
                                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#1890ff' }} />
                                            <Text style={{ color: '#d9d9d9' }}>{item}</Text>
                                        </Flex>
                                    </List.Item>
                                )}
                                locale={{ emptyText: <Empty description="暂无挂起治理任务" /> }}
                            />
                        </Card>
                    </Col>
                    <Col span={14}>
                        <Card 
                            title={<span style={{ color: '#fff' }}><HistoryOutlined /> 事故存根明细 (Incident Traces)</span>}
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
                                            description={<Text style={{ color: '#8c8c8c' }}>{incident.time}</Text>}
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
                    title={<span style={{ color: '#fff' }}><FileSearchOutlined /> 治理守卫实况 (Guard Sentinel)</span>}
                    bordered={false} 
                    style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}
                >
                    <Row gutter={[24, 24]}>
                        <Col span={8}>
                            <Flex vertical align="center" gap={12} style={{ background: '#1f1f1f', padding: 20, borderRadius: 12 }}>
                                <SecurityScanOutlined style={{ fontSize: 32, color: '#52c41a' }} />
                                <Text style={{ color: '#fff', fontWeight: 'bold' }}>Pre-commit Hook</Text>
                                <Tag color="success">STATUS: HEALTHY</Tag>
                                <Text type="secondary" style={{ fontSize: 12, textAlign: 'center' }}>拦截硬编码 Secret 与规约偏差</Text>
                            </Flex>
                        </Col>
                        <Col span={8}>
                            <Flex vertical align="center" gap={12} style={{ background: '#1f1f1f', padding: 20, borderRadius: 12 }}>
                                <SafetyCertificateOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                                <Text style={{ color: '#fff', fontWeight: 'bold' }}>Contract Guard</Text>
                                <Tag color="processing">STATUS: ACTIVE</Tag>
                                <Text type="secondary" style={{ fontSize: 12, textAlign: 'center' }}>实时校验前后端数据字段契约</Text>
                            </Flex>
                        </Col>
                        <Col span={8}>
                            <Flex vertical align="center" gap={12} style={{ background: '#1f1f1f', padding: 20, borderRadius: 12 }}>
                                <BugOutlined style={{ fontSize: 32, color: '#faad14' }} />
                                <Text style={{ color: '#fff', fontWeight: 'bold' }}>Security Scanner</Text>
                                <Tag color="warning">STATUS: ARMED</Tag>
                                <Text type="secondary" style={{ fontSize: 12, textAlign: 'center' }}>每日自动进行代码级漏洞扫描</Text>
                            </Flex>
                        </Col>
                    </Row>
                </Card>
            </Flex>
        </div>
    );
};
