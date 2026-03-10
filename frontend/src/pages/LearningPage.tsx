import React, { useState, useEffect } from 'react';
import { App, Button, List, Card, Tag, Space, Typography, Modal, Input, Tabs, Empty } from 'antd';
import { PlusOutlined, BulbOutlined, FireOutlined, GlobalOutlined, DeleteOutlined, RocketOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer } from '../components/common';
import { learningApi, type DailyLearningRun, type Subscription, type TechDiscovery } from '../services/learningApi';

const { Text, Paragraph } = Typography;

export const LearningPage: React.FC = () => {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const [discoveries, setDiscoveries] = useState<TechDiscovery[]>([]);
    const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
    const [loading, setLoading] = useState(false);
    const [dailyLoading, setDailyLoading] = useState(false);
    const [isSubModalOpen, setIsSubModalOpen] = useState(false);
    const [newTopic, setNewTopic] = useState('');
    const [dailyReports, setDailyReports] = useState<string[]>([]);
    const [latestRun, setLatestRun] = useState<DailyLearningRun | null>(null);
    const [selectedReportPath, setSelectedReportPath] = useState('');
    const [selectedReportContent, setSelectedReportContent] = useState('');
    const [previewLoading, setPreviewLoading] = useState(false);

    const loadData = async () => {
        setLoading(true);
        try {
            const [discRes, subRes] = await Promise.all([
                learningApi.getDiscoveries(),
                learningApi.getSubscriptions()
            ]);
            setDiscoveries(discRes.data.data);
            setSubscriptions(subRes.data.data);

            const reportsRes = await learningApi.getDailyReports(10);
            setDailyReports(reportsRes.data.data || []);
        } catch {
            message.error("加载数据失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleAddSub = async () => {
        if (!newTopic) return;
        try {
            await learningApi.addSubscription(newTopic);
            message.success("订阅成功");
            setNewTopic('');
            setIsSubModalOpen(false);
            loadData();
        } catch {
            message.error("订阅失败");
        }
    };

    const handleDeleteSub = async (id: string) => {
        try {
            await learningApi.deleteSubscription(id);
            message.success("已取消订阅");
            loadData();
        } catch {
            message.error("操作失败");
        }
    };

    const handleRunDailyCycle = async () => {
        setDailyLoading(true);
        try {
            const runRes = await learningApi.runDailyCycle();
            setLatestRun(runRes.data.data);
            message.success(`今日学习完成: ${runRes.data.data.report_path}`);
            const reportsRes = await learningApi.getDailyReports(10);
            setDailyReports(reportsRes.data.data || []);
        } catch {
            message.error('执行每日学习失败');
        } finally {
            setDailyLoading(false);
        }
    };

    const handlePreviewReport = async (reportPath: string) => {
        setPreviewLoading(true);
        try {
            const res = await learningApi.getDailyReportContent(reportPath);
            setSelectedReportPath(res.data.data.report_path);
            setSelectedReportContent(res.data.data.content || '');
        } catch {
            message.error('读取日报内容失败');
        } finally {
            setPreviewLoading(false);
        }
    };

    return (
        <PageContainer
            title={t('learning.title')}
            description={t('learning.description')}
            actions={
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsSubModalOpen(true)}>
                    {t('learning.add_sub')}
                </Button>
            }
        >
            <Space style={{ marginBottom: 16 }}>
                <Button type="default" icon={<BulbOutlined />} loading={dailyLoading} onClick={handleRunDailyCycle}>
                    运行每日自省学习
                </Button>
                {latestRun && <Tag color="success">最新报告: {latestRun.report_path}</Tag>}
                {latestRun && <Tag color="processing">多元信号: {latestRun.external_signals_count}</Tag>}
            </Space>

            <Tabs
                defaultActiveKey="1"
                items={[
                    {
                        key: '1',
                        label: <span><FireOutlined /> {t('learning.tabs.discovery')}</span>,
                        children: (
                            <List
                                grid={{ gutter: 16, column: 2 }}
                                loading={loading}
                                dataSource={discoveries}
                                renderItem={(item) => (
                                    <List.Item>
                                        <Card
                                            hoverable
                                            title={item.title}
                                            extra={<Tag color={item.relevance_score > 0.9 ? 'gold' : 'blue'}>关联度: {Math.round(item.relevance_score * 100)}%</Tag>}
                                            actions={[
                                                <Button type="link" icon={<GlobalOutlined />} onClick={() => window.open(item.url)}>查看原文</Button>,
                                                <Button type="link" icon={<RocketOutlined />}>应用此技术</Button>
                                            ]}
                                        >
                                            <Paragraph ellipsis={{ rows: 2 }}>{item.summary}</Paragraph>
                                            <Space separator={<Text type="secondary">|</Text>}>
                                                <Tag variant="filled">{item.category.toUpperCase()}</Tag>
                                                <Text type="secondary">{new Date(item.discovered_at).toLocaleDateString()}</Text>
                                            </Space>
                                        </Card>
                                    </List.Item>
                                )}
                                locale={{ emptyText: <Empty description="暂无新发现，尝试添加更多订阅" /> }}
                            />
                        )
                    },
                    {
                        key: '2',
                        label: <span><BulbOutlined /> {t('learning.tabs.my_subs')}</span>,
                        children: (
                            <List
                                loading={loading}
                                dataSource={subscriptions}
                                renderItem={(item) => (
                                    <List.Item
                                        actions={[
                                            <Button
                                                danger
                                                type="text"
                                                icon={<DeleteOutlined />}
                                                onClick={() => handleDeleteSub(item.id)}
                                            />
                                        ]}
                                    >
                                        <List.Item.Meta
                                            title={<Text strong>{item.topic}</Text>}
                                            description={`订阅于: ${new Date(item.created_at).toLocaleDateString()}`}
                                        />
                                        <Tag color="success">监控中</Tag>
                                    </List.Item>
                                )}
                                locale={{ emptyText: <Empty description="还没有任何订阅" /> }}
                            />
                        )
                    },
                    {
                        key: '3',
                        label: <span><RocketOutlined /> 每日学习报告</span>,
                        children: (
                            <Space direction="vertical" style={{ width: '100%' }} size="large">
                                <Card title="最近日报" size="small">
                                    <List
                                        dataSource={dailyReports}
                                        locale={{ emptyText: <Empty description="暂无日报，点击上方按钮执行一次" /> }}
                                        renderItem={(item) => (
                                            <List.Item
                                                actions={[
                                                    <Button type="link" onClick={() => handlePreviewReport(item)}>
                                                        预览内容
                                                    </Button>
                                                ]}
                                            >
                                                <Text code>{item}</Text>
                                            </List.Item>
                                        )}
                                    />
                                </Card>

                                <Card title={selectedReportPath ? `日报预览: ${selectedReportPath}` : '日报预览'} size="small" loading={previewLoading}>
                                    {selectedReportContent ? (
                                        <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{selectedReportContent}</pre>
                                    ) : (
                                        <Empty description="点击上方“预览内容”查看 Markdown 日报" />
                                    )}
                                </Card>

                                <Card title="最新改进建议" size="small">
                                    <List
                                        dataSource={latestRun?.suggestions || []}
                                        locale={{ emptyText: <Empty description="执行每日学习后可查看建议" /> }}
                                        renderItem={(item) => (
                                            <List.Item>
                                                <Space direction="vertical" style={{ width: '100%' }}>
                                                    <Text strong>{item.title}</Text>
                                                    <Text type="secondary">原因: {item.reason}</Text>
                                                    <Text>行动: {item.action}</Text>
                                                </Space>
                                            </List.Item>
                                        )}
                                    />
                                </Card>

                                <Card title="Agent+Skill 深度解读" size="small">
                                    {latestRun ? (
                                        <Space direction="vertical" style={{ width: '100%' }}>
                                            <Text>{latestRun.agent_summary}</Text>
                                            <Text strong>学习轨道</Text>
                                            <Space wrap>
                                                {(latestRun.learning_tracks || []).map((track) => (
                                                    <Tag key={track} color="purple">{track}</Tag>
                                                ))}
                                            </Space>
                                        </Space>
                                    ) : (
                                        <Empty description="执行每日学习后可查看深度解读" />
                                    )}
                                </Card>
                            </Space>
                        )
                    }
                ]}
            />

            <Modal
                title="添加技术订阅"
                open={isSubModalOpen}
                onOk={handleAddSub}
                onCancel={() => setIsSubModalOpen(false)}
                destroyOnHidden
            >
                <Paragraph>输入你想追踪的技术关键词（如：Spring Boot, LangChain, React 19），系统将自动搜寻相关动态。</Paragraph>
                <Input
                    placeholder="技术主题..."
                    value={newTopic}
                    onChange={e => setNewTopic(e.target.value)}
                    onPressEnter={handleAddSub}
                />
            </Modal>
        </PageContainer>
    );
};
