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

import React from 'react';
import { Row, Col, Card, Typography, Flex } from 'antd';
import {
    DatabaseOutlined,
    ClusterOutlined,
    BulbOutlined,
    ThunderboltOutlined,
    ArrowRightOutlined,
    RocketOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { StatCard } from '../components/common';
import styles from './DashboardPage.module.css';

const { Title, Text, Paragraph } = Typography;

/** 快捷入口 */
const quickActions = [
    {
        key: 'knowledge',
        icon: <DatabaseOutlined />,
        title: '知识库管理',
        desc: '上传文档，构建向量知识库',
        path: '/knowledge',
        color: '#06D6A0',
    },
    {
        key: 'agents',
        icon: <ClusterOutlined />,
        title: 'Agent 蜂巢',
        desc: '监控和管理 AI Agent 集群',
        path: '/agents',
        color: '#118AB2',
    },
    {
        key: 'learning',
        icon: <BulbOutlined />,
        title: '技术动态',
        desc: '追踪开源项目与技术趋势',
        path: '/learning',
        color: '#FFD166',
    },
];

export const DashboardPage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className={styles.container}>
            {/* === 欢迎区 === */}
            <div className={styles.hero}>
                <Flex align="center" gap={12} className={styles.heroLabel}>
                    <RocketOutlined />
                    <Text className={styles.heroLabelText}>AI-First RAG Platform</Text>
                </Flex>
                <Title level={2} className={styles.heroTitle}>
                    欢迎使用 <span className={styles.brand}>HiveMind</span>
                </Title>
                <Paragraph className={styles.heroDesc}>
                    通过右侧 AI 助手开始对话，或选择下方快捷入口直接操作。
                    AI 助手能理解你的意图并自动导航到对应功能。
                </Paragraph>
            </div>

            {/* === 统计概览 === */}
            <Row gutter={[16, 16]}>
                <Col xs={12} md={6}>
                    <StatCard title="知识库" value={0} icon={<DatabaseOutlined />} color="primary" />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard title="活跃 Agent" value={5} icon={<ClusterOutlined />} color="info" />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard title="今日对话" value={0} icon={<ThunderboltOutlined />} color="warning" />
                </Col>
                <Col xs={12} md={6}>
                    <StatCard title="技术发现" value={0} icon={<BulbOutlined />} color="success" />
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
                <Title level={5} className={styles.sectionTitle}>近期活动</Title>
                <Card className={styles.activityCard}>
                    <Flex align="center" justify="center" style={{ padding: 32 }}>
                        <Text type="secondary">暂无活动记录。通过右侧 AI 助手开始你的第一次对话 →</Text>
                    </Flex>
                </Card>
            </div>
        </div>
    );
};
