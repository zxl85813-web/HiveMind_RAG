import React from 'react';
import { Row, Col, Card, Typography, Flex, Tag, List, Progress, Space, Badge } from 'antd';
import {
    DatabaseOutlined,
    ClusterOutlined,
    BulbOutlined,
    ThunderboltOutlined,
    ArrowRightOutlined,
    RocketOutlined,
    LineChartOutlined,
    SafetyCertificateOutlined,
    AuditOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { StatCard } from '../components/common';
import { useDashboardStats, useRecentReports } from '../hooks/queries/useDashboardQuery';
import { useMonitor } from '../hooks/useMonitor';
import styles from './DashboardPage.module.css';

const { Title, Text, Paragraph } = Typography;

/**
 * 🛰️ [FE-GOV-001]: Dashboard 概览页面 (Refactored with React Query)
 */
export const DashboardPage: React.FC = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();

    // Server State
    const { data: stats, isLoading: loadingStats } = useDashboardStats();
    const { data: reports = [], isLoading: loadingReports } = useRecentReports(3);
    const { track } = useMonitor();

    React.useEffect(() => {
        track('system', 'page_load', { page: 'Dashboard' });
    }, [track]);

    /** 快捷入口 */
    const quickActions = [
        {
            key: 'knowledge',
            icon: <DatabaseOutlined />,
            title: t('nav.knowledge'),
            desc: i18n.language === 'zh-CN' ? '上传文档，构建向量知识库' : 'Upload docs and build vector KB',
            path: '/knowledge',
            color: 'var(--hm-color-brand)',
        },
        {
            key: 'agents',
            icon: <ClusterOutlined />,
            title: t('nav.agents'),
            desc: i18n.language === 'zh-CN' ? '监控和管理 AI Agent 集群' : 'Monitor and manage AI Agent swarm',
            path: '/agents',
            color: 'var(--hm-color-info)',
        },
        {
            key: 'learning',
            icon: <BulbOutlined />,
            title: t('nav.learning'),
            desc: i18n.language === 'zh-CN' ? '追踪开源项目与技术趋势' : 'Track open source and tech trends',
            path: '/learning',
            color: 'var(--hm-color-warning)',
        },
    ];

    return (
        <div className={styles.container}>
            {/* === 欢迎区 === */}
            <div className={styles.hero}>
                <Flex align="center" gap={12} className={styles.heroLabel}>
                    <RocketOutlined />
                    <Text className={styles.heroLabelText}>AI-First RAG Platform</Text>
                </Flex>
                <Title level={2} className={styles.heroTitle}>
                    {t('dashboard.welcome')} <span className={styles.brand}>HiveMind</span>
                </Title>
                <Paragraph className={styles.heroDesc}>
                    {t('dashboard.heroDesc')}
                </Paragraph>
            </div>

            {/* === 统计概览 === */}
            <Row gutter={[16, 16]}>
                <Col xs={12} md={6}>
                    <StatCard 
                        title={t('dashboard.stats.kbs')} 
                        value={stats?.total_kbs ?? 0} 
                        icon={<DatabaseOutlined />} 
                        color="primary" 
                        loading={loadingStats}
                    />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard 
                        title={t('dashboard.stats.agents')} 
                        value={stats?.active_agents ?? 0} 
                        icon={<ClusterOutlined />} 
                        color="info" 
                        loading={loadingStats}
                    />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard 
                        title={t('dashboard.stats.requests')} 
                        value={stats?.today_requests ?? 0} 
                        icon={<ThunderboltOutlined />} 
                        color="warning" 
                        loading={loadingStats}
                    />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard 
                        title={t('dashboard.stats.discoveries')} 
                        value={stats?.total_discoveries ?? 0} 
                        icon={<BulbOutlined />} 
                        color="success" 
                        loading={loadingStats}
                    />
                </Col>
            </Row>

            {/* === 快捷入口 === */}
            <div>
                <Title level={5} className={styles.sectionTitle}>快捷入口</Title>
                <Row gutter={[16, 16]}>
                    {quickActions.map((item) => (
                        <Col key={item.key} xs={24} md={8}>
                            <Card
                                hoverable
                                className={styles.actionCard}
                                onClick={() => navigate(item.path)}
                            >
                                <Flex vertical gap={12}>
                                    <div
                                        className={styles.actionIcon}
                                        style={{ color: item.color, background: `${item.color}15` }}
                                    >
                                        {item.icon}
                                    </div>
                                    <div>
                                        <Text strong className={styles.actionTitle}>{item.title}</Text>
                                        <Text type="secondary" className={styles.actionDesc}>{item.desc}</Text>
                                    </div>
                                    <Text className={styles.actionLink} style={{ color: item.color }}>
                                        进入 <ArrowRightOutlined />
                                    </Text>
                                </Flex>
                            </Card>
                        </Col>
                    ))}
                </Row>
            </div>

            {/* === 系统硬化进度 === */}
            <div style={{ marginTop: 24 }}>
                <Flex align="center" justify="space-between" className={styles.sectionTitle}>
                    <Title level={5} style={{ margin: 0 }}>系统工程化进度 (System Hardening)</Title>
                    <Tag icon={<SafetyCertificateOutlined />} color="cyan">治理指数: {stats?.hardening_score ?? 0}%</Tag>
                </Flex>
                <Card className={styles.hardeningCard}>
                    <Row gutter={32} align="middle">
                        <Col xs={24} md={16}>
                            <Paragraph>
                                HiveMind 正在从 <b>Mock/Stub 验证态</b> 迁移至 <b>生产高可用态</b>。目前的指标基于治理图谱中的真实代码实体与技术债节点比例计算。
                            </Paragraph>
                            <Progress 
                                percent={stats?.hardening_score ?? 0} 
                                status="active" 
                                strokeColor={{
                                    '0%': 'var(--hm-color-brand)',
                                    '100%': 'var(--hm-color-success)',
                                }}
                                strokeWidth={12}
                            />
                            <div style={{ marginTop: 16 }}>
                                <Space size="large">
                                    <Badge color="green" text={`正式组件: ${stats?.logic_entities ?? stats?.active_agents ?? 0}`} />
                                    <Badge color="red" text={`剩余技术债: ${stats?.debt_count ?? 0}`} />
                                </Space>
                            </div>
                        </Col>
                        <Col xs={24} md={8}>
                            <div style={{ textAlign: 'center', padding: '20px', borderLeft: '1px solid var(--hm-border-subtle)' }}>
                                <AuditOutlined style={{ fontSize: 48, color: 'var(--hm-color-brand-dim)', marginBottom: 12 }} />
                                <Title level={4} style={{ margin: 0 }}>{stats?.hardening_score > 90 ? '卓越' : stats?.hardening_score > 70 ? '良好' : '演进中'}</Title>
                                <Text type="secondary">架构可追溯性评价</Text>
                            </div>
                        </Col>
                    </Row>
                </Card>
            </div>

            {/* === 近期活动 === */}
            <div>
                <Title level={5} className={styles.sectionTitle}>近期质量报告</Title>
                <Card className={styles.activityCard} loading={loadingReports}>
                    {reports.length > 0 ? (
                        <Flex vertical gap={12}>
                            {reports.map((item) => (
                                <div 
                                    key={item.id}
                                    className={styles.reportItem}
                                    onClick={() => navigate('/evaluation')}
                                >
                                    <Flex align="center" justify="space-between">
                                        <Flex align="center" gap={12}>
                                            <LineChartOutlined style={{ fontSize: 24, color: 'var(--hm-color-brand)' }} />
                                            <div>
                                                <Text strong style={{ display: 'block' }}>{item.kb_name || 'Knowledge Base Evaluation'}</Text>
                                                <Text type="secondary" style={{ fontSize: 12 }}>
                                                    完成于 {new Date(item.created_at).toLocaleString()}
                                                </Text>
                                            </div>
                                        </Flex>
                                        <Flex align="center" gap={16}>
                                            <div style={{ width: 100 }}>
                                                <Progress 
                                                    percent={Math.round(item.total_score * 100)} 
                                                    size="small" 
                                                    showInfo={false} 
                                                    strokeColor={item.total_score > 0.7 ? 'var(--hm-color-success)' : 'var(--hm-color-warning)'} 
                                                />
                                            </div>
                                            <Tag color={item.total_score > 0.7 ? 'success' : item.total_score > 0.4 ? 'warning' : 'error'}>
                                                Score: {Math.round(item.total_score * 100)}%
                                            </Tag>
                                        </Flex>
                                    </Flex>
                                </div>
                            ))}
                        </Flex>
                    ) : (
                        <Flex align="center" justify="center" style={{ padding: 32 }}>
                            <Text type="secondary">暂无质量评估记录。建议前往「质量评估」模块生成测试集进行客观打分。</Text>
                        </Flex>
                    )}
                </Card>
            </div>
        </div>
    );
};
