
import React, { useState } from 'react';
import { Card, Form, Select, Input, Typography, Tabs, Table, Tag, Badge, Button, App, Popconfirm, Space, Modal, Tooltip, Flex } from 'antd';
import { SyncOutlined, PlusOutlined, DeleteOutlined, EditOutlined, SaveOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common';
import { useTranslation } from 'react-i18next';
import type { PlatformKnowledge, PlatformFeature, FAQItem } from '../services/settingsApi';
import { 
    useMcpStatus, 
    useMcpTools, 
    useSkills, 
    usePlatformKnowledge, 
    useUpdatePlatformKnowledgeMutation,
    useLlmGovernance,
    useUpdateLlmGovernanceMutation,
    useGovernanceTasks,
    useAdaptiveInsights
} from '../hooks/queries/useSettingsQuery';
import { useContractValidation } from '../hooks/useContractValidation';
import { BulbOutlined, InfoCircleOutlined, ThunderboltOutlined, DollarOutlined, ExperimentOutlined } from '@ant-design/icons';

const { Text } = Typography;
const { TextArea } = Input;

export const SettingsPage: React.FC = () => {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { validateStatus } = useContractValidation({ component: 'SettingsPage', action: 'view_mcp_status' });
    
    // Server State
    const { data: mcpStatus = [], isLoading: loadingMcp, refetch: refetchMcp, isRefetching: refetchingMcp } = useMcpStatus();
    const { data: mcpTools = [], isLoading: loadingTools } = useMcpTools();
    const { data: skills = [], isLoading: loadingSkills } = useSkills();
    const { data: platformKBData, isLoading: loadingPk } = usePlatformKnowledge();
    const updatePkMutation = useUpdatePlatformKnowledgeMutation();

    // Forms
    const [pkForm] = Form.useForm();

    // Data Sync
    React.useEffect(() => {
        if (platformKBData) {
            pkForm.setFieldsValue(platformKBData);
        }
    }, [platformKBData, pkForm]);

    const handleSavePk = async () => {
        try {
            const values = await pkForm.validateFields();
            await updatePkMutation.mutateAsync(values);
            message.success('平台知识库已保存');
        } catch {
            message.error('保存失败');
        }
    };

    const tabItems = [
        {
            key: 'llm',
            label: <span id="gov-tab-llm">🤖 {t('settings.llm')}</span>,
            children: <LlmGovernanceTab />
        },
        {
            key: 'mcp',
            label: <span>🔌 MCP & Skills</span>,
            children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                    <Card title="MCP Servers" extra={<Button size="small" icon={<SyncOutlined spin={refetchingMcp} />} onClick={() => refetchMcp()}>刷新</Button>}>
                        <Table dataSource={Array.isArray(mcpStatus) ? mcpStatus : []} rowKey="name" pagination={false} loading={loadingMcp} columns={[
                            { title: 'Server Name', dataIndex: 'name', key: 'name' },
                            { 
                                title: 'Status', 
                                dataIndex: 'status', 
                                key: 'status', 
                                render: (s) => {
                                    const validatedStatus = validateStatus(s, 'connected');
                                    return <Badge status={validatedStatus === 'connected' ? 'success' : 'error'} text={validatedStatus.toUpperCase()} />;
                                } 
                            },
                            { title: 'Transport', dataIndex: 'type', key: 'type' },
                        ]} />
                    </Card>
                    <Card title="Available MCP Tools">
                        <Table dataSource={Array.isArray(mcpTools) ? mcpTools : []} rowKey="name" size="small" loading={loadingTools} pagination={{ pageSize: 5 }} columns={[{ title: 'Tool Name', dataIndex: 'name' }, { title: 'Description', dataIndex: 'description' }]} />
                    </Card>
                    <Card title="Skill Registry">
                        <Table dataSource={Array.isArray(skills) ? skills : []} rowKey="name" size="small" loading={loadingSkills} pagination={{ pageSize: 5 }} columns={[{ title: 'Skill Name', dataIndex: 'name' }, { title: 'Version', dataIndex: 'version' }, { title: 'Status', dataIndex: 'status', render: (s) => <Badge status={s === 'active' ? 'success' : 'error'} text={s} /> }]} />
                    </Card>
                </Space>
            )
        },
        {
            key: 'knowledge',
            label: <span>🧠 平台知识库</span>,
            children: (
                <Form form={pkForm} layout="vertical">
                    <Card title="平台概述" loading={loadingPk} extra={<Button type="primary" size="small" icon={<SaveOutlined />} loading={updatePkMutation.isPending} onClick={handleSavePk}>保存</Button>}>
                        <Form.Item name="overview" style={{ marginBottom: 0 }}>
                            <TextArea rows={3} />
                        </Form.Item>
                    </Card>
                    <div style={{ marginTop: 16, color: '#888', textAlign: 'center' }}>
                        (提示：知识库详细功能模块配置请查阅 _platform_knowledge.yaml)
                    </div>
                </Form>
            )
        }
    ];

    return (
        <PageContainer title={t('settings.title')} description={t('settings.description')} maxWidth={900}>
            <Tabs defaultActiveKey="llm" items={tabItems} />
        </PageContainer>
    );
};

const LlmGovernanceTab: React.FC = () => {
    const { data: config, isLoading, refetch } = useLlmGovernance();
    const { data: insights = [] } = useAdaptiveInsights();
    const updateMutation = useUpdateLlmGovernanceMutation();
    const { message } = App.useApp();
    const [form] = Form.useForm();
    const [hasInitialized, setHasInitialized] = React.useState(false);

    // Registry editing state
    const [isRegistryModalOpen, setIsRegistryModalOpen] = useState(false);
    const [editingModel, setEditingModel] = useState<any>(null);

    React.useEffect(() => {
        if (config && !hasInitialized) {
            form.setFieldsValue(config);
            setHasInitialized(true);
        }
    }, [config, form, hasInitialized]);

    const onSave = async () => {
        try {
            const values = await form.validateFields();
            await updateMutation.mutateAsync({
                ...config,
                ...values
            });
            message.success('治理策略已更新');
            refetch();
        } catch (e) {
            message.error('保存失败');
        }
    };

    const handleEditModel = (model: any) => {
        setEditingModel(model);
        setIsRegistryModalOpen(true);
    };

    if (isLoading) return <Card loading bordered={false} style={{ background: 'transparent' }} />;

    const modelOptions = config?.model_registry?.map(m => ({ label: m.name, value: m.id })) || [];

    return (
        <Flex vertical gap={24} style={{ width: '100%' }}>
            {/* 1. Adaptive Insights - Premium Look */}
            <AdaptiveInsights insights={insights} />

            {/* 2. Tier Routing - Balanced UI */}
            <Card 
                title={<Space><ThunderboltOutlined style={{ color: '#06D6A0' }} /> <span>模型梯队路由 (Dynamic Tiering)</span></Space>} 
                extra={<Button type="primary" size="middle" icon={<SaveOutlined />} onClick={onSave} loading={updateMutation.isPending} style={{ borderRadius: 6 }}>推送治理规则</Button>}
                bordered={false}
                style={{ background: '#111827', borderRadius: 12, border: '1px solid rgba(255,255,255,0.05)' }}
            >
                <Form form={form} layout="vertical">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
                        <Form.Item label={<span>简单任务 <Tooltip title="即时回复、纠错、闲聊"><InfoCircleOutlined /></Tooltip></span>} name={['tier_mapping', 'simple']}>
                            <Select options={modelOptions} placeholder="选择模型" size="large" />
                        </Form.Item>
                        <Form.Item label={<span>中等任务 <Tooltip title="摘要、结构化抽取、文本分析"><InfoCircleOutlined /></Tooltip></span>} name={['tier_mapping', 'medium']}>
                            <Select options={modelOptions} placeholder="选择模型" size="large" />
                        </Form.Item>
                        <Form.Item label={<span>复杂任务 <Tooltip title="代码编写、流程规划、数学推演"><InfoCircleOutlined /></Tooltip></span>} name={['tier_mapping', 'complex']}>
                            <Select options={modelOptions} placeholder="选择模型" size="large" />
                        </Form.Item>
                        <Form.Item label={<span>推理任务 <Tooltip title="深度思考 (Chain of Thought)、逻辑闭环"><InfoCircleOutlined /></Tooltip></span>} name={['tier_mapping', 'reasoning']}>
                            <Select options={modelOptions} placeholder="选择模型" size="large" />
                        </Form.Item>
                    </div>
                </Form>
            </Card>

            {/* 3. Model Knowledge Base - More detailed */}
            <ModelKnowledgeBase 
                registry={config?.model_registry || []} 
                onEdit={handleEditModel} 
                onAdd={() => {
                    setEditingModel(null);
                    setIsRegistryModalOpen(true);
                }}
            />

            {/* 4. Escalation Pipeline - Fixed styling */}
            <GovernanceTaskTable />

            <Modal
                title={editingModel ? `编辑模型: ${editingModel.name}` : '添加模型'}
                open={isRegistryModalOpen}
                onCancel={() => setIsRegistryModalOpen(false)}
                footer={null}
                width={600}
                centered
            >
                <Form 
                    layout="vertical" 
                    initialValues={editingModel || { provider: 'openai', characteristics: [], usage_scenarios: [] }}
                    onFinish={async (values) => {
                        const loadingHide = message.loading('正在同步模型智库...', 0);
                        try {
                            const currentRegistry = [...(config?.model_registry || [])];
                            let newRegistry;
                            
                            if (editingModel) {
                                // Update existing
                                newRegistry = currentRegistry.map(m => 
                                    m.id === editingModel.id ? { ...m, ...values } : m
                                );
                            } else {
                                // Add new (auto-generate ID if missing)
                                const newModel = { 
                                    ...values, 
                                    id: values.id || `${values.provider}/${values.name.toLowerCase().replace(/\s+/g, '-')}`,
                                    status: 'active'
                                };
                                newRegistry = [...currentRegistry, newModel];
                            }

                            await updateMutation.mutateAsync({
                                ...config,
                                model_registry: newRegistry
                            });
                            
                            message.success('模型智库已更新');
                            setIsRegistryModalOpen(false);
                            refetch();
                        } catch (e) {
                            message.error('同步失败: ' + (e as any).message);
                        } finally {
                            loadingHide();
                        }
                    }}
                >
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <Form.Item label="标识 ID (唯一)" name="id" extra="留空将根据供应商和名称自动生成" hidden={!!editingModel}>
                            <Input placeholder="例如: deepseek-ai/DeepSeek-V3" disabled={!!editingModel} />
                        </Form.Item>
                        <Form.Item label="名称" name="name" rules={[{ required: true }]}><Input /></Form.Item>
                        <Form.Item label="供应商" name="provider" rules={[{ required: true }]}>
                            <Select options={[
                                { label: 'SiliconFlow (Recommended)', value: 'siliconflow' },
                                { label: 'Volcengine Ark', value: 'ark' },
                                { label: 'OpenAI', value: 'openai' }, 
                                { label: 'Anthropic', value: 'anthropic' }, 
                                { label: 'DeepSeek (Official)', value: 'deepseek' }, 
                                { label: 'Local (Ollama)', value: 'ollama' }
                            ]} />
                        </Form.Item>
                        <Form.Item label="输入价格 (1M)" name="input_price_1m"><Input prefix={<DollarOutlined />} /></Form.Item>
                        <Form.Item label="输出价格 (1M)" name="output_price_1m"><Input prefix={<DollarOutlined />} /></Form.Item>
                    </div>
                    <Form.Item label="技术特性" name="characteristics">
                        <Select mode="tags" placeholder="输入并回车，如: Low Latency, 128K Context" />
                    </Form.Item>
                    <Form.Item label="最佳场景" name="usage_scenarios">
                        <Select mode="tags" placeholder="如: Chat, Coding, Agent" />
                    </Form.Item>
                    <div style={{ textAlign: 'right', marginTop: 12 }}>
                        <Space>
                            <Button onClick={() => setIsRegistryModalOpen(false)}>取消</Button>
                            <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>保存更新</Button>
                        </Space>
                    </div>
                </Form>
            </Modal>

        </Flex>
    );
};

const AdaptiveInsights: React.FC<{ insights: any[] }> = ({ insights }) => {
    if (!insights || insights.length === 0) return null;
    
    return (
        <Card 
            size="small" 
            title={<Space><BulbOutlined style={{ color: '#FFD166' }} /> <span style={{ color: '#fff', fontSize: '15px' }}>自治推荐 (Autonomous Advice)</span></Space>} 
            style={{ 
                background: 'linear-gradient(145deg, #111827 0%, #1f2937 100%)', 
                border: '1px solid rgba(6, 214, 160, 0.2)',
                borderRadius: 12,
                boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
            }}
        >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', padding: '12px 0' }}>
                {insights.map((item, idx) => (
                    <div key={idx} style={{ 
                        padding: '16px', 
                        borderRadius: '10px', 
                        background: 'rgba(255,255,255,0.03)', 
                        border: '1px solid rgba(255,255,255,0.08)',
                        position: 'relative',
                        overflow: 'hidden'
                    }}>
                        <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: item.type === 'cost' ? '#06D6A0' : item.type === 'performance' ? '#118AB2' : '#FFD166' }} />
                        <Flex justify="space-between" align="center" style={{ marginBottom: '10px' }}>
                            <Text strong style={{ color: '#eee' }}>{item.title}</Text>
                            <Tag color={item.priority === 'high' ? 'error' : item.priority === 'medium' ? 'warning' : 'default'} style={{ fontSize: '10px' }}>
                                {item.priority.toUpperCase()}
                            </Tag>
                        </Flex>
                        <Text type="secondary" style={{ fontSize: '12.5px', lineHeight: 1.6, display: 'block' }}>{item.content}</Text>
                    </div>
                ))}
            </div>
            <div style={{ marginTop: 8, padding: '0 8px' }}>
                <Text type="secondary" style={{ fontSize: '11px', fontStyle: 'italic' }}>
                    * 系统已根据过去 24h 的 Token 消耗与成功率自动生成以上建议。
                </Text>
            </div>
        </Card>
    );
};

const ModelKnowledgeBase: React.FC<{ registry: any[], onEdit: (m: any) => void, onAdd: () => void }> = ({ registry, onEdit, onAdd }) => {
    const columns = [
        { 
            title: '模型标识', dataIndex: 'name', key: 'name', 
            render: (text: string, record: any) => (
                <Space vertical align="start" size={0}>
                    <Text strong style={{ color: '#06D6A0' }}>{text}</Text>
                    <Text type="secondary" style={{ fontSize: '11px' }}>ID: {record.id}</Text>
                </Space>
            )
        },
        { 
            title: '价格 (1M Tokens)', key: 'price',
            render: (_: any, record: any) => (
                <div style={{ fontSize: '12px' }}>
                    <div style={{ marginBottom: 2 }}><Badge color="#118AB2" text={<Text type="secondary">In:</Text>} /> <Text strong>${record.input_price_1m}</Text></div>
                    <div><Badge color="#06D6A0" text={<Text type="secondary">Out:</Text>} /> <Text strong>${record.output_price_1m}</Text></div>
                </div>
            )
        },
        { 
            title: '特性 / 最佳场景', key: 'traits',
            render: (_: any, record: any) => (
                <Flex vertical gap={4}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {record.characteristics?.map((c: string) => <Tag key={c} color="blue" style={{ fontSize: '10px', borderRadius: 4 }}>{c}</Tag>)}
                    </div>
                    <Text type="secondary" style={{ fontSize: '11px' }}>🎯 {record.usage_scenarios?.join('、')}</Text>
                </Flex>
            )
        },
        {
            title: '操作', key: 'action', width: 70,
            render: (_: any, record: any) => (
                <Button type="text" icon={<EditOutlined />} onClick={() => onEdit(record)} style={{ color: '#06D6A0' }} />
            )
        }
    ];

    return (
        <Card 
            title={<Space><ExperimentOutlined /> <span>模型智库 (Model Registry & Profiles)</span></Space>} 
            extra={<Button size="small" icon={<PlusOutlined />} onClick={onAdd} style={{ color: '#06D6A0' }}>添加模型</Button>}
            styles={{ body: { padding: 0 } }}
            bordered={false}
            style={{ background: '#111827', borderRadius: 12, border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden' }}
        >
            <Table 
                dataSource={registry} 
                columns={columns} 
                rowKey="id" 
                pagination={false} 
                size="middle" 
                style={{ background: 'transparent' }}
                className="governance-table"
            />
        </Card>
    );
};

const GovernanceTaskTable: React.FC = () => {
    const { data: tasks = [], isLoading, refetch, isRefetching } = useGovernanceTasks();
    const { message } = App.useApp();
    const [syncing, setSyncing] = React.useState(false);

    const handleSync = async () => {
        setSyncing(true);
        try {
            await import('../services/api').then(m => m.default.post('/settings/llm/governance/sync'));
            message.success('智体同步成功，已更新全局治理图谱');
            refetch();
        } catch (e) {
            message.error('同步失败');
        } finally {
            setSyncing(false);
        }
    };

    const columns = [
        { title: '任务 ID', dataIndex: 'id', key: 'id', width: 140, render: (id: string) => <Text code style={{ color: '#FFD166', background: 'rgba(255,209,102,0.1)', border: 'none' }}>{id}</Text> },
        { title: '异常/待办描述', dataIndex: 'title', key: 'title', ellipsis: true, render: (t: string) => <Text style={{ color: '#ddd' }}>{t}</Text> },
        { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (s: string) => <Tag bordered={false} color={s === 'RESOLVED' ? 'success' : 'processing'}>{s}</Tag> },
        { title: '检测时间', dataIndex: 'created_at', key: 'time', width: 160, render: (t: string) => <Text type="secondary" style={{ fontSize: '12px' }}>{new Date(t).toLocaleString()}</Text> },
        { 
            title: '深度透视', key: 'action', width: 90, 
            render: (_: any, record: any) => (
                <Button 
                    type="link" 
                    href={record.snapshot_url} 
                    target="_blank" 
                    rel="noreferrer"
                    style={{ fontSize: '13px', color: '#06D6A0', padding: 0 }}
                >
                    查看快照
                </Button>
            ) 
        }
    ];

    return (
        <Card 
            size="small" 
            title={<Space><SafetyCertificateOutlined /> <span>自治任务流水线 (Agentic Pipeline)</span></Space>} 
            style={{ 
                marginTop: 8, 
                border: '1px solid rgba(255, 255, 255, 0.08)', 
                background: '#111827',
                borderRadius: 12,
                boxShadow: 'inset 0 0 20px rgba(0,0,0,0.1)'
            }} 
            extra={<Button size="small" type="dashed" icon={<SyncOutlined spin={syncing || isRefetching} />} onClick={handleSync} style={{ fontSize: '12px' }}>同步实时图谱</Button>}
        >
            <Table 
                dataSource={Array.isArray(tasks) ? tasks : []} 
                columns={columns} 
                rowKey="id" 
                size="small" 
                loading={isLoading} 
                pagination={{ pageSize: 5 }} 
                style={{ background: 'transparent' }}
            />
        </Card>
    );
};
