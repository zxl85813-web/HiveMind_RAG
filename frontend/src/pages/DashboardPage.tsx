/**
 * DashboardPage — 概览首页。
 *
 * AI-First 架构中的默认落地页:
 *   - 欢迎区域 + 快速入口
 *   - 摘要统计
 *   - 近期活动
 *
 * 不再是空白 ChatPage — 对话功能在右侧 ChatPanel 中。
 *
 * @module pages
 * @see docs/design/ai-first-frontend.md
 */

import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Typography, Flex } from 'antd';
import {
    DatabaseOutlined,
    ClusterOutlined,
    BulbOutlined,
    ThunderboltOutlined,
    ArrowRightOutlined,
    RocketOutlined,
    LineChartOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { StatCard } from '../components/common';
import { agentApi } from '../services/agentApi';
import { knowledgeApi } from '../services/knowledgeApi';
import { evalApi } from '../services/evalApi';
import { Tag, List, Progress } from 'antd';
import styles from './DashboardPage.module.css';

const { Title, Text, Paragraph } = Typography;

export const DashboardPage: React.FC = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();

    /** 快捷入口 */
    const quickActions = [
        {
            key: 'knowledge',
            icon: <DatabaseOutlined />,
            title: t('nav.knowledge'),
            desc: i18n.language === 'zh-CN' ? '上传文档，构建向量知识库' : 'Upload docs and build vector KB',
            path: '/knowledge',
            color: '#06D6A0',
        },
        {
            key: 'agents',
            icon: <ClusterOutlined />,
            title: t('nav.agents'),
            desc: i18n.language === 'zh-CN' ? '监控和管理 AI Agent 集群' : 'Monitor and manage AI Agent swarm',
            path: '/agents',
            color: '#118AB2',
        },
        {
            key: 'learning',
            icon: <BulbOutlined />,
            title: t('nav.learning'),
            desc: i18n.language === 'zh-CN' ? '追踪开源项目与技术趋势' : 'Track open source and tech trends',
            path: '/learning',
            color: '#FFD166',
        },
    ];
    const { data: stats, isLoading: statsLoading } = useDashboardStats();
    const { data: reports, isLoading: reportsLoading } = useRecentReports();

    const recentReports = reports || [
        { id: '1', kb_name: 'Core Docs', total_score: 0.85, created_at: new Date().toISOString() },
        { id: '2', kb_name: 'API Reference', total_score: 0.42, created_at: new Date().toISOString() }
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
                    <StatCard title={t('dashboard.stats.kbs')} value={stats.kbs} icon={<DatabaseOutlined />} color="primary" />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard title={t('dashboard.stats.agents')} value={stats.agents} icon={<ClusterOutlined />} color="info" />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard title={t('dashboard.stats.requests')} value={stats.requests} icon={<ThunderboltOutlined />} color="warning" />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard title={t('dashboard.stats.discoveries')} value={stats.discoveries} icon={<BulbOutlined />} color="success" />
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

            {/* === 近期活动 (占位) === */}
            <div>
                <Title level={5} className={styles.sectionTitle}>近期质量报告</Title>
                <Card className={styles.activityCard} loading={loadingReports}>
                    {recentReports.length > 0 ? (
                        <List
                            itemLayout="horizontal"
                            dataSource={recentReports}
                            renderItem={(item) => (
                                <List.Item
                                    style={{ cursor: 'pointer' }}
                                    onClick={() => navigate('/evaluation')}
                                    extra={<Tag color={item.total_score > 0.7 ? 'success' : item.total_score > 0.4 ? 'warning' : 'error'}>Score: {Math.round(item.total_score * 100)}%</Tag>}
                                >
                                    <List.Item.Meta
                                        avatar={<LineChartOutlined style={{ fontSize: 24, color: 'var(--hm-color-brand)' }} />}
                                        title={<Text strong>{item.kb_name || 'Knowledge Base Evaluation'}</Text>}
                                        description={<Text type="secondary" style={{ fontSize: 12 }}>完成于 {new Date(item.created_at).toLocaleString()}</Text>}
                                    />
                                    <div style={{ width: 120 }}>
                                        <Progress percent={Math.round(item.total_score * 100)} size="small" showInfo={false} strokeColor={item.total_score > 0.7 ? '#52c41a' : '#faad14'} />
                                    </div>
                                </List.Item>
                            )}
                        />
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
