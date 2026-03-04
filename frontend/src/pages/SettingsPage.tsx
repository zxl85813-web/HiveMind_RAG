/**
 * SettingsPage — 系统设置页面。
 *
 * 使用通用组件: PageContainer
 *
 * @module pages
 * @see REGISTRY.md > 前端 > 页面 > SettingsPage
 */

import React, { useState, useEffect } from 'react';
import { Card, Form, Select, Switch, Input, Typography, Tabs, Row, Col, Table, Tag, Badge, Button, message, Popconfirm, Space, Modal } from 'antd';
import { SyncOutlined, PlusOutlined, DeleteOutlined, EditOutlined, SaveOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common';
import { useTranslation } from 'react-i18next';
import { agentApi, type McpServerStatus, type McpTool, type SkillInfo } from '../services/agentApi';
import { settingsApi, type PlatformKnowledge, type PlatformFeature, type FAQItem } from '../services/settingsApi';

const { Text } = Typography;
const { TextArea } = Input;

export const SettingsPage: React.FC = () => {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(false);
    const [mcpStatus, setMcpStatus] = useState<McpServerStatus[]>([]);
    const [mcpTools, setMcpTools] = useState<McpTool[]>([]);
    const [skills, setSkills] = useState<SkillInfo[]>([]);

    // === Platform Knowledge State ===
    const [pkLoading, setPkLoading] = useState(false);
    const [pkSaving, setPkSaving] = useState(false);
    const [platformKB, setPlatformKB] = useState<PlatformKnowledge>({
        overview: '',
        features: [],
        faq: [],
    });
    const [featureModalOpen, setFeatureModalOpen] = useState(false);
    const [faqModalOpen, setFaqModalOpen] = useState(false);
    const [editingFeature, setEditingFeature] = useState<PlatformFeature>({ name: '', path: '', description: '', operations: [] });
    const [editingFaq, setEditingFaq] = useState<FAQItem>({ q: '', a: '' });
    const [editingFeatureIndex, setEditingFeatureIndex] = useState<number | null>(null);
    const [editingFaqIndex, setEditingFaqIndex] = useState<number | null>(null);
    const [operationsText, setOperationsText] = useState('');

    const fetchMCPData = async () => {
        setLoading(true);
        try {
            const [statusRes, toolsRes, skillsRes] = await Promise.all([
                agentApi.getMcpStatus(),
                agentApi.getMcpTools(),
                agentApi.getSkills()
            ]);
            setMcpStatus(statusRes.data.data || []);
            setMcpTools(toolsRes.data.data || []);
            setSkills(skillsRes.data.data || []);
        } catch (error) {
            message.error("Failed to load MCP & Skills data");
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const fetchPlatformKB = async () => {
        setPkLoading(true);
        try {
            const res = await settingsApi.getPlatformKnowledge();
            setPlatformKB(res.data);
        } catch (error) {
            console.error('Failed to load platform knowledge:', error);
            // If API not available, leave defaults
        } finally {
            setPkLoading(false);
        }
    };

    const savePlatformKB = async (data?: PlatformKnowledge) => {
        const toSave = data || platformKB;
        setPkSaving(true);
        try {
            await settingsApi.updatePlatformKnowledge(toSave);
            setPlatformKB(toSave);
            message.success('平台知识库已保存，AI 即刻生效');
        } catch (error) {
            message.error('保存失败');
            console.error(error);
        } finally {
            setPkSaving(false);
        }
    };

    // Feature CRUD
    const openAddFeature = () => {
        setEditingFeature({ name: '', path: '/', description: '', operations: [] });
        setOperationsText('');
        setEditingFeatureIndex(null);
        setFeatureModalOpen(true);
    };

    const openEditFeature = (feature: PlatformFeature, index: number) => {
        setEditingFeature({ ...feature });
        setOperationsText(feature.operations.join('\n'));
        setEditingFeatureIndex(index);
        setFeatureModalOpen(true);
    };

    const saveFeature = async () => {
        const feat = {
            ...editingFeature,
            operations: operationsText.split('\n').map(s => s.trim()).filter(Boolean),
        };
        const updated = { ...platformKB };
        if (editingFeatureIndex !== null) {
            updated.features[editingFeatureIndex] = feat;
        } else {
            updated.features = [...updated.features, feat];
        }
        await savePlatformKB(updated);
        setFeatureModalOpen(false);
    };

    const deleteFeature = async (index: number) => {
        const updated = {
            ...platformKB,
            features: platformKB.features.filter((_, i) => i !== index),
        };
        await savePlatformKB(updated);
    };

    // FAQ CRUD
    const openAddFaq = () => {
        setEditingFaq({ q: '', a: '' });
        setEditingFaqIndex(null);
        setFaqModalOpen(true);
    };

    const openEditFaq = (faq: FAQItem, index: number) => {
        setEditingFaq({ ...faq });
        setEditingFaqIndex(index);
        setFaqModalOpen(true);
    };

    const saveFaq = async () => {
        const updated = { ...platformKB };
        if (editingFaqIndex !== null) {
            updated.faq[editingFaqIndex] = editingFaq;
        } else {
            updated.faq = [...updated.faq, editingFaq];
        }
        await savePlatformKB(updated);
        setFaqModalOpen(false);
    };

    const deleteFaq = async (index: number) => {
        const updated = {
            ...platformKB,
            faq: platformKB.faq.filter((_, i) => i !== index),
        };
        await savePlatformKB(updated);
    };

    useEffect(() => {
        fetchMCPData();
        fetchPlatformKB();
    }, []);

    // === Feature Table Columns ===
    const featureColumns = [
        {
            title: '功能名称',
            dataIndex: 'name',
            key: 'name',
            width: 140,
            render: (text: string) => <Text strong>{text}</Text>,
        },
        {
            title: '路径',
            dataIndex: 'path',
            key: 'path',
            width: 120,
            render: (text: string) => <Tag color="blue">{text}</Tag>,
        },
        {
            title: '描述',
            dataIndex: 'description',
            key: 'desc',
            ellipsis: true,
        },
        {
            title: '操作说明',
            dataIndex: 'operations',
            key: 'ops',
            width: 80,
            render: (ops: string[]) => <Tag>{ops?.length || 0} 条</Tag>,
        },
        {
            title: '操作',
            key: 'action',
            width: 100,
            render: (_: any, record: PlatformFeature, index: number) => (
                <Space size="small">
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditFeature(record, index)} />
                    <Popconfirm title="确认删除?" onConfirm={() => deleteFeature(index)}>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    // === FAQ Table Columns ===
    const faqColumns = [
        {
            title: '问题',
            dataIndex: 'q',
            key: 'q',
            width: '40%',
        },
        {
            title: '回答',
            dataIndex: 'a',
            key: 'a',
            ellipsis: true,
        },
        {
            title: '操作',
            key: 'action',
            width: 100,
            render: (_: any, record: FAQItem, index: number) => (
                <Space size="small">
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditFaq(record, index)} />
                    <Popconfirm title="确认删除?" onConfirm={() => deleteFaq(index)}>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <PageContainer
            title={t('settings.title')}
            description={t('settings.description')}
            maxWidth={900}
        >
            <Tabs defaultActiveKey="llm">
                <Tabs.TabPane tab={<span>🤖 {t('settings.llm')}</span>} key="llm">
                    <Card>
                        <Form layout="vertical">
                            <Form.Item label="默认对话模型">
                                <Select
                                    defaultValue="gpt-4o-mini"
                                    options={[
                                        { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                                        { value: 'gpt-4o', label: 'GPT-4o' },
                                        { value: 'deepseek-v3', label: 'DeepSeek V3' },
                                        { value: 'deepseek-r1', label: 'DeepSeek R1 (推理)' },
                                        { value: 'qwen-turbo', label: '通义千问 Turbo' },
                                    ]}
                                />
                            </Form.Item>
                            <Form.Item label="默认推理模型">
                                <Select
                                    defaultValue="deepseek-r1"
                                    options={[
                                        { value: 'deepseek-r1', label: 'DeepSeek R1' },
                                        { value: 'gpt-4o', label: 'GPT-4o' },
                                    ]}
                                />
                            </Form.Item>
                        </Form>
                    </Card>

                    <Card title={`🐝 ${t('settings.agent')}`} style={{ marginTop: '16px' }}>
                        <Form layout="vertical">
                            <Form.Item label="自省模式">
                                <Switch defaultChecked />
                                <Text type="secondary" style={{ marginLeft: 8 }}>
                                    Agent 会在回答后自动进行质量评估
                                </Text>
                            </Form.Item>
                            <Form.Item label="主动建议">
                                <Switch defaultChecked />
                                <Text type="secondary" style={{ marginLeft: 8 }}>
                                    AI 助手会主动推送相关建议和提醒
                                </Text>
                            </Form.Item>
                        </Form>
                    </Card>
                </Tabs.TabPane>

                <Tabs.TabPane tab={<span>🔑 API Keys</span>} key="api">
                    <Card>
                        <Form layout="vertical">
                            <Form.Item label="OpenAI API Key">
                                <Input.Password placeholder="sk-..." />
                            </Form.Item>
                            <Form.Item label="DeepSeek API Key">
                                <Input.Password placeholder="sk-..." />
                            </Form.Item>
                        </Form>
                    </Card>
                </Tabs.TabPane>

                <Tabs.TabPane tab={<span>🔌 MCP & Skills</span>} key="mcp">
                    <Row gutter={[16, 16]}>
                        <Col span={24}>
                            <Card title="Model Context Protocol (MCP) Servers"
                                extra={<Button type="primary" size="small" icon={<SyncOutlined spin={loading} />} onClick={fetchMCPData}>刷新状态</Button>}>
                                <Table
                                    dataSource={mcpStatus}
                                    rowKey="name"
                                    pagination={false}
                                    columns={[
                                        { title: 'Server Name', dataIndex: 'name', key: 'name', render: (text) => <Text strong>{text}</Text> },
                                        { title: 'Status', dataIndex: 'status', key: 'status', render: (status) => <Badge status={status === 'connected' ? 'success' : 'error'} text={status.toUpperCase()} /> },
                                        { title: 'Transport', dataIndex: 'type', key: 'type', render: (type) => <Tag color="blue">{type}</Tag> },
                                        { title: 'Command', key: 'cmd', render: (_, record) => <Text code>{record.command} {record.args.join(' ')}</Text> },
                                    ]}
                                />
                            </Card>
                        </Col>

                        <Col span={24}>
                            <Card title="Available MCP Tools" style={{ marginTop: 16 }}>
                                <Table
                                    dataSource={mcpTools}
                                    rowKey="name"
                                    size="small"
                                    pagination={{ pageSize: 5 }}
                                    columns={[
                                        { title: 'Tool Name', dataIndex: 'name', key: 'name', render: (text) => <Tag color="geekblue">{text}</Tag> },
                                        { title: 'Description', dataIndex: 'description', key: 'desc', render: (text) => <Text type="secondary">{text}</Text> },
                                    ]}
                                />
                            </Card>
                        </Col>

                        <Col span={24}>
                            <Card title="Skill Registry (Meta-Skills)" style={{ marginTop: 16 }}>
                                <Table
                                    dataSource={skills}
                                    rowKey="name"
                                    size="small"
                                    pagination={{ pageSize: 5 }}
                                    columns={[
                                        { title: 'Skill Name', dataIndex: 'name', key: 'name', render: (text) => <Tag color="purple">{text}</Tag> },
                                        { title: 'Version', dataIndex: 'version', key: 'version' },
                                        { title: 'Description', dataIndex: 'description', key: 'desc', render: (text) => <Text type="secondary">{text}</Text> },
                                        { title: 'Status', dataIndex: 'status', key: 'status', render: (status) => <Badge status={status === 'active' ? 'success' : 'error'} text={status.toUpperCase()} /> },
                                    ]}
                                />
                            </Card>
                        </Col>
                    </Row>
                </Tabs.TabPane>

                {/* ====== 平台知识库管理 Tab ====== */}
                <Tabs.TabPane tab={<span>🧠 平台知识库</span>} key="knowledge">
                    <Card
                        title="平台概述"
                        extra={
                            <Button
                                type="primary"
                                size="small"
                                icon={<SaveOutlined />}
                                loading={pkSaving}
                                onClick={() => savePlatformKB()}
                            >
                                保存全部
                            </Button>
                        }
                        loading={pkLoading}
                    >
                        <TextArea
                            value={platformKB.overview}
                            onChange={(e) => setPlatformKB({ ...platformKB, overview: e.target.value })}
                            rows={3}
                            placeholder="描述平台的核心功能和定位..."
                        />
                        <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
                            此内容会注入到每个 AI Agent 的系统提示词中，让 AI 了解平台功能。
                        </Text>
                    </Card>

                    <Card
                        title="功能模块"
                        style={{ marginTop: 16 }}
                        extra={
                            <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openAddFeature}>
                                添加功能
                            </Button>
                        }
                    >
                        <Table
                            dataSource={platformKB.features}
                            columns={featureColumns}
                            rowKey="name"
                            size="small"
                            pagination={false}
                        />
                    </Card>

                    <Card
                        title="常见问答 (FAQ)"
                        style={{ marginTop: 16 }}
                        extra={
                            <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openAddFaq}>
                                添加 FAQ
                            </Button>
                        }
                    >
                        <Table
                            dataSource={platformKB.faq}
                            columns={faqColumns}
                            rowKey={(_, i) => String(i)}
                            size="small"
                            pagination={false}
                        />
                    </Card>
                </Tabs.TabPane>
            </Tabs>

            {/* === 功能模块编辑弹窗 === */}
            <Modal
                title={editingFeatureIndex !== null ? '编辑功能模块' : '添加功能模块'}
                open={featureModalOpen}
                onCancel={() => setFeatureModalOpen(false)}
                onOk={saveFeature}
                okText="保存"
                confirmLoading={pkSaving}
            >
                <Form layout="vertical">
                    <Form.Item label="功能名称" required>
                        <Input
                            value={editingFeature.name}
                            onChange={(e) => setEditingFeature({ ...editingFeature, name: e.target.value })}
                            placeholder="如: 知识库管理"
                        />
                    </Form.Item>
                    <Form.Item label="路由路径" required>
                        <Input
                            value={editingFeature.path}
                            onChange={(e) => setEditingFeature({ ...editingFeature, path: e.target.value })}
                            placeholder="如: /knowledge"
                        />
                    </Form.Item>
                    <Form.Item label="功能描述" required>
                        <TextArea
                            value={editingFeature.description}
                            onChange={(e) => setEditingFeature({ ...editingFeature, description: e.target.value })}
                            rows={2}
                            placeholder="如: 创建和管理知识库，上传文档..."
                        />
                    </Form.Item>
                    <Form.Item label="操作说明 (每行一条)">
                        <TextArea
                            value={operationsText}
                            onChange={(e) => setOperationsText(e.target.value)}
                            rows={4}
                            placeholder={"创建知识库: 点击「创建知识库」按钮\n上传文档: 进入详情页点击上传"}
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* === FAQ 编辑弹窗 === */}
            <Modal
                title={editingFaqIndex !== null ? '编辑 FAQ' : '添加 FAQ'}
                open={faqModalOpen}
                onCancel={() => setFaqModalOpen(false)}
                onOk={saveFaq}
                okText="保存"
                confirmLoading={pkSaving}
            >
                <Form layout="vertical">
                    <Form.Item label="问题" required>
                        <Input
                            value={editingFaq.q}
                            onChange={(e) => setEditingFaq({ ...editingFaq, q: e.target.value })}
                            placeholder="用户会问的问题"
                        />
                    </Form.Item>
                    <Form.Item label="回答" required>
                        <TextArea
                            value={editingFaq.a}
                            onChange={(e) => setEditingFaq({ ...editingFaq, a: e.target.value })}
                            rows={3}
                            placeholder="AI 应该如何回答"
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </PageContainer>
    );
};
