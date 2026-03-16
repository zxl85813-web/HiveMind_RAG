import React, { useState } from 'react';
import { Card, Form, Select, Input, Typography, Tabs, Table, Tag, Badge, Button, App, Popconfirm, Space, Modal } from 'antd';
import { SyncOutlined, PlusOutlined, DeleteOutlined, EditOutlined, SaveOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common';
import { useTranslation } from 'react-i18next';
import type { PlatformKnowledge, PlatformFeature, FAQItem } from '../services/settingsApi';
import { 
    useMcpStatus, 
    useMcpTools, 
    useSkills, 
    usePlatformKnowledge, 
    useUpdatePlatformKnowledgeMutation 
} from '../hooks/queries/useSettingsQuery';

const { Text } = Typography;
const { TextArea } = Input;

/**
 * 🛰️ [FE-GOV-001]: 系统设置页面 (Refactored with React Query)
 */
export const SettingsPage: React.FC = () => {
    const { t } = useTranslation();
    const { message } = App.useApp();
    
    // Server State
    const { data: mcpStatus = [], isLoading: loadingMcp, refetch: refetchMcp, isRefetching: refetchingMcp } = useMcpStatus();
    const { data: mcpTools = [], isLoading: loadingTools } = useMcpTools();
    const { data: skills = [], isLoading: loadingSkills } = useSkills();
    const { data: platformKBData, isLoading: loadingPk } = usePlatformKnowledge();
    const updatePkMutation = useUpdatePlatformKnowledgeMutation();

    // Local UI State for Editing (cloning server state)
    const [localPlatformKB, setLocalPlatformKB] = useState<PlatformKnowledge | null>(null);
    const [featureModalOpen, setFeatureModalOpen] = useState(false);
    const [faqModalOpen, setFaqModalOpen] = useState(false);
    const [editingFeature, setEditingFeature] = useState<PlatformFeature>({ name: '', path: '', description: '', operations: [] });
    const [editingFaq, setEditingFaq] = useState<FAQItem>({ q: '', a: '' });
    const [editingFeatureIndex, setEditingFeatureIndex] = useState<number | null>(null);
    const [editingFaqIndex, setEditingFaqIndex] = useState<number | null>(null);
    const [operationsText, setOperationsText] = useState('');

    // Sync local state when server data is loaded
    React.useEffect(() => {
        if (platformKBData && !localPlatformKB) {
            setLocalPlatformKB(platformKBData);
        }
    }, [platformKBData, localPlatformKB]);

    const activePlatformKB = localPlatformKB || platformKBData || { overview: '', features: [], faq: [] };

    const handleSaveAll = async (data?: PlatformKnowledge) => {
        const toSave = data || activePlatformKB;
        try {
            await updatePkMutation.mutateAsync(toSave);
            message.success('平台知识库已保存，AI 即刻生效');
        } catch {
            message.error('保存失败');
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
        const updated = { ...activePlatformKB };
        if (editingFeatureIndex !== null) {
            updated.features[editingFeatureIndex] = feat;
        } else {
            updated.features = [...updated.features, feat];
        }
        setLocalPlatformKB(updated);
        await handleSaveAll(updated);
        setFeatureModalOpen(false);
    };

    const deleteFeature = async (index: number) => {
        const updated = {
            ...activePlatformKB,
            features: activePlatformKB.features.filter((_, i) => i !== index),
        };
        setLocalPlatformKB(updated);
        await handleSaveAll(updated);
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
        const updated = { ...activePlatformKB };
        if (editingFaqIndex !== null) {
            updated.faq[editingFaqIndex] = editingFaq;
        } else {
            updated.faq = [...updated.faq, editingFaq];
        }
        setLocalPlatformKB(updated);
        await handleSaveAll(updated);
        setFaqModalOpen(false);
    };

    const deleteFaq = async (index: number) => {
        const updated = {
            ...activePlatformKB,
            faq: activePlatformKB.faq.filter((_, i) => i !== index),
        };
        setLocalPlatformKB(updated);
        await handleSaveAll(updated);
    };

    // Columns
    const featureColumns = [
        { title: '功能名称', dataIndex: 'name', key: 'name', width: 140, render: (text: string) => <Text strong>{text}</Text> },
        { title: '路径', dataIndex: 'path', key: 'path', width: 120, render: (text: string) => <Tag color="blue">{text}</Tag> },
        { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true },
        { title: '操作说明', dataIndex: 'operations', key: 'ops', width: 80, render: (ops: string[]) => <Tag>{ops?.length || 0} 条</Tag> },
        {
            title: '操作', key: 'action', width: 100,
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

    const faqColumns = [
        { title: '问题', dataIndex: 'q', key: 'q', width: '40%' },
        { title: '回答', dataIndex: 'a', key: 'a', ellipsis: true },
        {
            title: '操作', key: 'action', width: 100,
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
        <PageContainer title={t('settings.title')} description={t('settings.description')} maxWidth={900}>
            <Tabs defaultActiveKey="llm">
                <Tabs.TabPane tab={<span>🤖 {t('settings.llm')}</span>} key="llm">
                    <Card>
                        <Form layout="vertical">
                            <Form.Item label="默认对话模型">
                                <Select defaultValue="gpt-4o-mini" options={[{ value: 'gpt-4o-mini', label: 'GPT-4o Mini' }]} />
                            </Form.Item>
                        </Form>
                    </Card>
                </Tabs.TabPane>

                <Tabs.TabPane tab={<span>🔌 MCP & Skills</span>} key="mcp">
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Card title="MCP Servers" extra={<Button size="small" icon={<SyncOutlined spin={refetchingMcp} />} onClick={() => refetchMcp()}>刷新</Button>}>
                            <Table dataSource={mcpStatus} rowKey="name" pagination={false} loading={loadingMcp} columns={[
                                { title: 'Server Name', dataIndex: 'name', key: 'name' },
                                { title: 'Status', dataIndex: 'status', key: 'status', render: (s) => <Badge status={s === 'connected' ? 'success' : 'error'} text={s.toUpperCase()} /> },
                                { title: 'Transport', dataIndex: 'type', key: 'type' },
                            ]} />
                        </Card>
                        <Card title="Available MCP Tools">
                            <Table dataSource={mcpTools} rowKey="name" size="small" loading={loadingTools} pagination={{ pageSize: 5 }} columns={[{ title: 'Tool Name', dataIndex: 'name' }, { title: 'Description', dataIndex: 'description' }]} />
                        </Card>
                        <Card title="Skill Registry">
                            <Table dataSource={skills} rowKey="name" size="small" loading={loadingSkills} pagination={{ pageSize: 5 }} columns={[{ title: 'Skill Name', dataIndex: 'name' }, { title: 'Version', dataIndex: 'version' }, { title: 'Status', dataIndex: 'status', render: (s) => <Badge status={s === 'active' ? 'success' : 'error'} text={s} /> }]} />
                        </Card>
                    </Space>
                </Tabs.TabPane>

                <Tabs.TabPane tab={<span>🧠 平台知识库</span>} key="knowledge">
                    <Card title="平台概述" loading={loadingPk} extra={<Button type="primary" size="small" icon={<SaveOutlined />} loading={updatePkMutation.isPending} onClick={() => handleSaveAll()}>保存全部</Button>}>
                        <TextArea value={activePlatformKB.overview} onChange={(e) => setLocalPlatformKB({ ...activePlatformKB, overview: e.target.value })} rows={3} />
                    </Card>

                    <Card title="功能模块" style={{ marginTop: 16 }} extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={openAddFeature}>添加功能</Button>}>
                        <Table dataSource={activePlatformKB.features} columns={featureColumns} rowKey="name" size="small" pagination={false} />
                    </Card>

                    <Card title="常见问答 (FAQ)" style={{ marginTop: 16 }} extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={openAddFaq}>添加 FAQ</Button>}>
                        <Table dataSource={activePlatformKB.faq} columns={faqColumns} rowKey={(_, i) => String(i)} size="small" pagination={false} />
                    </Card>
                </Tabs.TabPane>
            </Tabs>

            {/* Modals for Edit/Add */}
            <Modal title={editingFeatureIndex !== null ? '编辑功能模块' : '添加功能模块'} open={featureModalOpen} onCancel={() => setFeatureModalOpen(false)} onOk={saveFeature} okText="保存" confirmLoading={updatePkMutation.isPending}>
                <Form layout="vertical">
                    <Form.Item label="功能名称" required><Input value={editingFeature.name} onChange={(e) => setEditingFeature({ ...editingFeature, name: e.target.value })} /></Form.Item>
                    <Form.Item label="路由路径" required><Input value={editingFeature.path} onChange={(e) => setEditingFeature({ ...editingFeature, path: e.target.value })} /></Form.Item>
                    <Form.Item label="描述" required><TextArea value={editingFeature.description} onChange={(e) => setEditingFeature({ ...editingFeature, description: e.target.value })} rows={2} /></Form.Item>
                    <Form.Item label="操作说明"><TextArea value={operationsText} onChange={(e) => setOperationsText(e.target.value)} rows={4} /></Form.Item>
                </Form>
            </Modal>

            <Modal title={editingFaqIndex !== null ? '编辑 FAQ' : '添加 FAQ'} open={faqModalOpen} onCancel={() => setFaqModalOpen(false)} onOk={saveFaq} okText="保存" confirmLoading={updatePkMutation.isPending}>
                <Form layout="vertical">
                    <Form.Item label="问题" required><Input value={editingFaq.q} onChange={(e) => setEditingFaq({ ...editingFaq, q: e.target.value })} /></Form.Item>
                    <Form.Item label="回答" required><TextArea value={editingFaq.a} onChange={(e) => setEditingFaq({ ...editingFaq, a: e.target.value })} rows={3} /></Form.Item>
                </Form>
            </Modal>
        </PageContainer>
    );
};
