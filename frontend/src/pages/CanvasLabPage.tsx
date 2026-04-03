import React from 'react';
import { Card, Tabs, Typography, Tag, Space, Row, Col } from 'antd';
import { PageContainer } from '../components/common';
import { G6SimpleGraph, X6SimpleCanvas } from '../components/canvas';
import styles from './CanvasLabPage.module.css';
import { useMonitor } from '../hooks/useMonitor';

const { Paragraph, Text } = Typography;

export const CanvasLabPage: React.FC = () => {
    const { track } = useMonitor();
    
    React.useEffect(() => {
        track('system', 'page_load', { page: 'CanvasLab' });
    }, [track]);
    return (
        <PageContainer
            title="Canvas Lab"
            description="升级版 simple demos：支持 AI 无限画布工作流（任意位置加节点、自动连线、缩放平移与聚焦）。"
        >
            <div className={styles.container}>
                <Card className={styles.heroCard}>
                    <Space direction="vertical" size={10}>
                        <Text className={styles.heroTitle}>AI + Canvas 技术验证面板</Text>
                        <Paragraph className={styles.tip}>
                            这里聚焦“可落地可迁移”：保留简单结构，但补齐无限画布交互感，作为后续替换
                            `PipelineBuilder`、`AgentDAGVisualizer` 的起点模板。
                        </Paragraph>
                        <Space size={8} wrap>
                            <Tag color="processing">X6 Flow</Tag>
                            <Tag color="cyan">G6 Graph</Tag>
                            <Tag color="success">Interactive Toolbar</Tag>
                            <Tag color="warning">AI-ready Components</Tag>
                        </Space>
                    </Space>
                </Card>

                <Row gutter={[12, 12]}>
                    <Col xs={24} md={8}>
                        <Card className={styles.featureCard}>
                            <Text strong>1. 结构化编排</Text>
                            <Paragraph className={styles.featureText}>X6 demo 支持节点追加、框选、连接，可逐步迁移到真实 Pipeline 配置。</Paragraph>
                        </Card>
                    </Col>
                    <Col xs={24} md={8}>
                        <Card className={styles.featureCard}>
                            <Text strong>2. 关系洞察</Text>
                            <Paragraph className={styles.featureText}>G6 demo 支持关系图聚焦与缩放，适合作为 Agent 协作链路展示基线。</Paragraph>
                        </Card>
                    </Col>
                    <Col xs={24} md={8}>
                        <Card className={styles.featureCard}>
                            <Text strong>3. AI 生成复用</Text>
                            <Paragraph className={styles.featureText}>组件结构已对齐系统台账，后续 AI 生成前端会优先复用这些画布组件。</Paragraph>
                        </Card>
                    </Col>
                </Row>

                <Card className={styles.canvasCard}>
                    <Tabs
                        defaultActiveKey="x6"
                        items={[
                            {
                                key: 'x6',
                                label: 'X6 Flow Demo',
                                children: (
                                    <React.Suspense fallback={<Card loading style={{ height: 420 }} />}>
                                        <X6SimpleCanvas />
                                    </React.Suspense>
                                ),
                            },
                            {
                                key: 'g6',
                                label: 'G6 Graph Demo',
                                children: (
                                    <React.Suspense fallback={<Card loading style={{ height: 420 }} />}>
                                        <G6SimpleGraph />
                                    </React.Suspense>
                                ),
                            },
                        ]}
                    />
                </Card>
            </div>
        </PageContainer>
    );
};
