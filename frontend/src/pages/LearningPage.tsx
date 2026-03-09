import React, { useState, useEffect } from 'react';
import { App, Button, List, Card, Tag, Space, Typography, Modal, Input, Tabs, Empty } from 'antd';
import { PlusOutlined, BulbOutlined, FireOutlined, GlobalOutlined, DeleteOutlined, RocketOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer } from '../components/common';
import { learningApi, type Subscription, type TechDiscovery } from '../services/learningApi';

const { Text, Paragraph } = Typography;

export const LearningPage: React.FC = () => {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const [discoveries, setDiscoveries] = useState<TechDiscovery[]>([]);
    const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
    const [loading, setLoading] = useState(false);
    const [isSubModalOpen, setIsSubModalOpen] = useState(false);
    const [newTopic, setNewTopic] = useState('');

    const loadData = async () => {
        setLoading(true);
        try {
            const [discRes, subRes] = await Promise.all([
                learningApi.getDiscoveries(),
                learningApi.getSubscriptions()
            ]);
            setDiscoveries(discRes.data.data);
            setSubscriptions(subRes.data.data);
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
