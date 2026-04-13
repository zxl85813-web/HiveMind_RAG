
import React from 'react';
import { Card, Row, Col, Statistic, List, Tag, Progress, Flex, Typography, Alert, Empty } from 'antd';
import { 
    SafetyCertificateOutlined, 
    HistoryOutlined, 
    CheckCircleOutlined, 
    WarningOutlined,
    RocketOutlined,
    SecurityScanOutlined,
    BugOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Title, Text } = Typography;

export const DevGovernancePage: React.FC = () => {
    const { t } = useTranslation();

    const { data: stats, isLoading } = useQuery({
        queryKey: ['dev-governance-stats'],
        queryFn: async () => {
            const res = await api.get('/governance/dev-stats');
            return res.data.data;
        }
    });

    return (
        <div style={{ padding: 24, background: '#0a0a0a', minHeight: '100%' }}>
            <Flex vertical gap={24}>
                <Flex align="center" gap={16}>
                    <SafetyCertificateOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                    <div>
                        <Title level={2} style={{ color: '#fff', margin: 0 }}>研发治理中心</Title>
                        <Text style={{ color: '#8c8c8c' }}>AI-First 架构自省与工程合规实时看板</Text>
                    </div>
                </Flex>

                <Row gutter={[16, 16]}>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12 }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>代码合规分 (Compliance)</Text>}
                                value={stats?.compliance_score || 0}
                                precision={1}
                                valueStyle={{ color: '#52c41a' }}
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
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12 }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>已拦截事故 (Incidents)</Text>}
                                value={stats?.total_incidents || 0}
                                valueStyle={{ color: '#faad14' }}
                                prefix={<WarningOutlined />}
                            />
                            <Text style={{ color: '#595959', fontSize: 12 }}>最近 30 天拦截</Text>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12 }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>智体完成任务 (TODO)</Text>}
                                value={stats?.todo_stats?.done || 0}
                                valueStyle={{ color: '#1890ff' }}
                                prefix={<RocketOutlined />}
                            />
                            <Text style={{ color: '#595959', fontSize: 12 }}>待处理: {stats?.todo_stats?.active || 0}</Text>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card bordered={false} style={{ background: '#141414', borderRadius: 12 }}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c' }}>中文注释覆盖率</Text>}
                                value={stats?.annotations_coverage?.replace('%', '') || 0}
                                precision={1}
                                valueStyle={{ color: '#eb2f96' }}
                                suffix="%"
                            />
                            <Progress 
                                percent={parseFloat(stats?.annotations_coverage || '0')} 
                                showInfo={false} 
                                strokeColor="#eb2f96"
                                trailColor="#262626"
                                style={{ marginTop: 12 }}
                            />
                        </Card>
                    </Col>
                </Row>

                <Row gutter={[16, 16]}>
                    <Col span={16}>
                        <Card 
                            title={<span style={{ color: '#fff' }}><HistoryOutlined /> 治理守卫状态 (Harness)</span>}
                            bordered={false} 
                            style={{ background: '#141414', borderRadius: 12 }}
                        >
                            <Row gutter={[24, 24]}>
                                <Col span={8}>
                                    <Flex vertical align="center" gap={12}>
                                        <SecurityScanOutlined style={{ fontSize: 40, color: '#52c41a' }} />
                                        <Text style={{ color: '#fff' }}>Pre-commit Hook</Text>
                                        <Tag color="success">HEALTHY</Tag>
                                    </Flex>
                                </Col>
                                <Col span={8}>
                                    <Flex vertical align="center" gap={12}>
                                        <SafetyCertificateOutlined style={{ fontSize: 40, color: '#1890ff' }} />
                                        <Text style={{ color: '#fff' }}>Contract Guard</Text>
                                        <Tag color="processing">ACTIVE</Tag>
                                    </Flex>
                                </Col>
                                <Col span={8}>
                                    <Flex vertical align="center" gap={12}>
                                        <BugOutlined style={{ fontSize: 40, color: '#faad14' }} />
                                        <Text style={{ color: '#fff' }}>Security Scanner</Text>
                                        <Tag color="warning">ARMED</Tag>
                                    </Flex>
                                </Col>
                            </Row>
                            
                            <Alert
                                message="治理建议"
                                description="检测到后端存储路径已完成绝对路径收拢，建议进行一次全量图谱对齐校验。"
                                type="info"
                                showIcon
                                style={{ marginTop: 24, background: '#001529', border: '1px solid #1890ff' }}
                            />
                        </Card>
                    </Col>
                    <Col span={8}>
                        <Card 
                            title={<span style={{ color: '#fff' }}>最新事故存根</span>}
                            bordered={false} 
                            style={{ background: '#141414', borderRadius: 12, height: '100%' }}
                        >
                             <Empty 
                                image={Empty.PRESENTED_IMAGE_SIMPLE} 
                                description={<Text style={{ color: '#595959' }}>暂无未处理事故</Text>} 
                             />
                        </Card>
                    </Col>
                </Row>
            </Flex>
        </div>
    );
};
