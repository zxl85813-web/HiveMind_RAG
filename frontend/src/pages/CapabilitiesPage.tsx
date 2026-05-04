/**
 * CapabilitiesPage — Agent 能力中心 (MCP Servers / Skills / Tools 的统一管理入口)。
 *
 * 提供:
 *   - MCP Servers 健康状态总览
 *   - Skills 注册表浏览 + 详情查看
 *   - MCP Tools 列表与所属 Server 标记
 *   - 能力拓扑全屏视图
 *
 * @module pages
 */

import React, { useEffect, useState, useMemo } from 'react';
import {
    Row, Col, Tabs, Card, Table, Tag, Badge, Typography, Button, Space,
    Input, Drawer, Modal, message, Empty, Statistic, Tooltip, Form, Popconfirm, Switch, Upload
} from 'antd';
import {
    ApiOutlined, ThunderboltOutlined, ApartmentOutlined, SyncOutlined,
    SearchOutlined, EyeOutlined, ClusterOutlined, CodeOutlined,
    PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
    UploadOutlined, InboxOutlined
} from '@ant-design/icons';
import type { UploadFile } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PageContainer, StatCard } from '../components/common';
import { SwarmTopologyMap } from '../components/agents/SwarmTopologyMap';
import {
    agentApi,
    type McpServerStatus, type McpTool, type SkillInfo,
    type SkillDetail, type TopologyData
} from '../services/agentApi';

const { Text, Paragraph } = Typography;

export const CapabilitiesPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<string>('topology');

    const [mcpStatus, setMcpStatus] = useState<McpServerStatus[]>([]);
    const [mcpTools, setMcpTools] = useState<McpTool[]>([]);
    const [skills, setSkills] = useState<SkillInfo[]>([]);
    const [topology, setTopology] = useState<TopologyData>({ nodes: [], links: [] });

    const [skillKeyword, setSkillKeyword] = useState('');
    const [toolKeyword, setToolKeyword] = useState('');

    const [skillDetailOpen, setSkillDetailOpen] = useState(false);
    const [skillDetail, setSkillDetail] = useState<SkillDetail | null>(null);
    const [skillDetailLoading, setSkillDetailLoading] = useState(false);

    const [serverModalOpen, setServerModalOpen] = useState(false);
    const [activeServer, setActiveServer] = useState<McpServerStatus | null>(null);

    // === MCP Server Edit Form ===
    const [editOpen, setEditOpen] = useState(false);
    const [editMode, setEditMode] = useState<'create' | 'update'>('create');
    const [editSubmitting, setEditSubmitting] = useState(false);
    const [editForm] = Form.useForm<{ name: string; command: string; argsText: string; type: string }>();

    // === Skill install/uninstall/toggle ===
    const [installOpen, setInstallOpen] = useState(false);
    const [installFile, setInstallFile] = useState<UploadFile | null>(null);
    const [installOverwrite, setInstallOverwrite] = useState(false);
    const [installSubmitting, setInstallSubmitting] = useState(false);
    const [skillTogglePending, setSkillTogglePending] = useState<string | null>(null);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [statusRes, toolsRes, skillsRes, topoRes] = await Promise.all([
                agentApi.getMcpStatus(),
                agentApi.getMcpTools(),
                agentApi.getSkills(),
                agentApi.getTopology(),
            ]);
            setMcpStatus(statusRes.data.data || []);
            setMcpTools(toolsRes.data.data || []);
            setSkills(skillsRes.data.data || []);
            setTopology(topoRes.data.data || { nodes: [], links: [] });
        } catch (e) {
            message.error('加载能力数据失败');
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAll(); }, []);

    const openSkillDetail = async (name: string) => {
        setSkillDetailOpen(true);
        setSkillDetail(null);
        setSkillDetailLoading(true);
        try {
            const res = await agentApi.getSkillDetail(name);
            setSkillDetail(res.data.data);
        } catch (e) {
            message.error(`无法加载 Skill 详情: ${name}`);
            console.error(e);
        } finally {
            setSkillDetailLoading(false);
        }
    };

    // === MCP Server CRUD ===
    const openCreateServer = () => {
        setEditMode('create');
        editForm.resetFields();
        editForm.setFieldsValue({ type: 'stdio', argsText: '' });
        setEditOpen(true);
    };

    const openEditServer = (s: McpServerStatus) => {
        setEditMode('update');
        editForm.setFieldsValue({
            name: s.name,
            type: s.type || 'stdio',
            command: s.command,
            argsText: (s.args || []).join(' '),
        });
        setEditOpen(true);
    };

    const submitServer = async () => {
        const values = await editForm.validateFields();
        const args = values.argsText
            ? values.argsText.split(/\s+/).filter(Boolean)
            : [];
        setEditSubmitting(true);
        try {
            await agentApi.upsertMcpServer({
                name: values.name.trim(),
                type: values.type || 'stdio',
                command: values.command.trim(),
                args,
            });
            message.success(`MCP Server 已${editMode === 'create' ? '添加' : '更新'}，正在重连…`);
            setEditOpen(false);
            await fetchAll();
        } catch (e) {
            message.error('保存失败');
            console.error(e);
        } finally {
            setEditSubmitting(false);
        }
    };

    const deleteServer = async (name: string) => {
        try {
            await agentApi.deleteMcpServer(name);
            message.success(`已删除 MCP Server: ${name}`);
            await fetchAll();
        } catch (e) {
            message.error('删除失败');
            console.error(e);
        }
    };

    const reconnectAll = async () => {
        try {
            await agentApi.reconnectMcp();
            message.success('所有 MCP Server 已重新连接');
            await fetchAll();
        } catch (e) {
            message.error('重连失败');
            console.error(e);
        }
    };

    // === Skill ops ===
    const submitInstall = async () => {
        if (!installFile?.originFileObj) {
            message.warning('请选择 ZIP 文件');
            return;
        }
        setInstallSubmitting(true);
        try {
            const res = await agentApi.installSkill(installFile.originFileObj as File, installOverwrite);
            message.success(`Skill "${res.data.data.name}" 已安装`);
            setInstallOpen(false);
            setInstallFile(null);
            setInstallOverwrite(false);
            await fetchAll();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '安装失败');
            console.error(e);
        } finally {
            setInstallSubmitting(false);
        }
    };

    const uninstallSkill = async (name: string) => {
        try {
            await agentApi.uninstallSkill(name, true);
            message.success(`Skill "${name}" 已卸载`);
            await fetchAll();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '卸载失败');
            console.error(e);
        }
    };

    const toggleSkill = async (name: string, enabled: boolean) => {
        setSkillTogglePending(name);
        try {
            await agentApi.toggleSkill(name, enabled);
            await fetchAll();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '切换失败');
            console.error(e);
        } finally {
            setSkillTogglePending(null);
        }
    };

    const reloadSkills = async () => {
        try {
            const res = await agentApi.reloadSkills();
            message.success(`已重载 ${res.data.data.skill_count} 个 Skill`);
            await fetchAll();
        } catch (e) {
            message.error('重载失败');
            console.error(e);
        }
    };

    const filteredSkills = useMemo(
        () => skills.filter(s =>
            !skillKeyword ||
            s.name.toLowerCase().includes(skillKeyword.toLowerCase()) ||
            ((s.summary || s.description) || '').toLowerCase().includes(skillKeyword.toLowerCase())
        ),
        [skills, skillKeyword]
    );

    const filteredTools = useMemo(
        () => mcpTools.filter(t =>
            !toolKeyword ||
            t.name.toLowerCase().includes(toolKeyword.toLowerCase()) ||
            (t.description || '').toLowerCase().includes(toolKeyword.toLowerCase())
        ),
        [mcpTools, toolKeyword]
    );

    const connectedCount = mcpStatus.filter(s => s.status === 'connected').length;
    const isSkillEnabled = (s: SkillInfo) =>
        s.enabled !== undefined ? !!s.enabled : s.status !== 'inactive' && s.status !== 'error';
    const activeSkillCount = skills.filter(isSkillEnabled).length;

    // === Tabs Content ===

    const renderTopology = () => (
        <Card
            styles={{ body: { padding: 0, height: 600, overflow: 'hidden', borderRadius: '0 0 12px 12px' } }}
            style={{ borderRadius: 12, background: 'rgba(0,0,0,0.2)', border: '1px solid #1f1f1f' }}
        >
            {topology.nodes.length > 0 ? (
                <SwarmTopologyMap data={topology} height={600} />
            ) : (
                <Empty description="暂无拓扑数据" style={{ padding: 60 }} />
            )}
        </Card>
    );

    const renderMcpServers = () => (
        <Card
            title={
                <Space>
                    <ApiOutlined style={{ color: '#06b6d4' }} />
                    <span>MCP Servers</span>
                    <Tag color="cyan">{connectedCount} / {mcpStatus.length} 在线</Tag>
                </Space>
            }
            extra={
                <Space>
                    <Button size="small" icon={<PlusOutlined />} type="primary" onClick={openCreateServer}>
                        添加 Server
                    </Button>
                    <Button size="small" icon={<ReloadOutlined />} onClick={reconnectAll}>
                        全部重连
                    </Button>
                    <Button size="small" icon={<SyncOutlined spin={loading} />} onClick={fetchAll}>刷新</Button>
                </Space>
            }
        >
            <Table
                dataSource={mcpStatus}
                rowKey="name"
                pagination={false}
                size="middle"
                locale={{ emptyText: <Empty description="尚未配置任何 MCP Server" /> }}
                columns={[
                    {
                        title: 'Server', dataIndex: 'name', key: 'name', width: 180,
                        render: (text) => <Text strong style={{ color: '#06b6d4' }}>{text}</Text>
                    },
                    {
                        title: '状态', dataIndex: 'status', key: 'status', width: 120,
                        render: (s) => <Badge status={s === 'connected' ? 'success' : 'error'} text={s.toUpperCase()} />
                    },
                    {
                        title: 'Transport', dataIndex: 'type', key: 'type', width: 100,
                        render: (t) => <Tag color="blue">{t}</Tag>
                    },
                    {
                        title: '启动命令', key: 'cmd',
                        render: (_, r) => <Text code style={{ fontSize: 12 }}>{r.command} {r.args.join(' ')}</Text>
                    },
                    {
                        title: '操作', key: 'action', width: 200, fixed: 'right',
                        render: (_, r) => (
                            <Space size="small">
                                <Button type="link" size="small" icon={<EyeOutlined />}
                                    onClick={() => { setActiveServer(r); setServerModalOpen(true); }}>
                                    详情
                                </Button>
                                <Button type="link" size="small" icon={<EditOutlined />}
                                    onClick={() => openEditServer(r)}>
                                    编辑
                                </Button>
                                <Popconfirm
                                    title={`确定删除 "${r.name}"?`}
                                    description="将立即从配置文件移除并断开连接"
                                    onConfirm={() => deleteServer(r.name)}
                                    okType="danger"
                                >
                                    <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                                        删除
                                    </Button>
                                </Popconfirm>
                            </Space>
                        )
                    },
                ]}
            />
        </Card>
    );

    const renderSkills = () => (
        <Card
            title={
                <Space>
                    <ThunderboltOutlined style={{ color: '#a855f7' }} />
                    <span>Skills 注册表</span>
                    <Tag color="purple">{activeSkillCount} / {skills.length} 启用</Tag>
                </Space>
            }
            extra={
                <Space>
                    <Input
                        prefix={<SearchOutlined />}
                        placeholder="搜索 Skill"
                        allowClear
                        value={skillKeyword}
                        onChange={e => setSkillKeyword(e.target.value)}
                        style={{ width: 220 }}
                        size="small"
                    />
                    <Button size="small" icon={<ReloadOutlined />} onClick={reloadSkills}>
                        重新扫描
                    </Button>
                    <Button type="primary" size="small" icon={<UploadOutlined />} onClick={() => setInstallOpen(true)}>
                        安装 Skill 包
                    </Button>
                </Space>
            }
        >
            <Table
                dataSource={filteredSkills}
                rowKey="name"
                size="middle"
                pagination={{ pageSize: 10, hideOnSinglePage: true }}
                columns={[
                    {
                        title: 'Skill', dataIndex: 'name', key: 'name', width: 200,
                        render: (text) => <Tag color="purple" style={{ fontSize: 12 }}>{text}</Tag>
                    },
                    {
                        title: '版本', dataIndex: 'version', key: 'version', width: 90,
                        render: (v) => <Text type="secondary" style={{ fontFamily: 'monospace' }}>{v || '—'}</Text>
                    },
                    {
                        title: '描述', key: 'desc',
                        render: (_, r) => <Text type="secondary">{r.summary || r.description || '—'}</Text>
                    },
                    {
                        title: '工具数', dataIndex: 'tool_count', key: 'tool_count', width: 80,
                        render: (n) => <Tag color="cyan">{n ?? 0}</Tag>
                    },
                    {
                        title: '启用', key: 'enabled', width: 80,
                        render: (_, r) => (
                            <Switch
                                size="small"
                                checked={isSkillEnabled(r)}
                                loading={skillTogglePending === r.name}
                                onChange={(checked) => toggleSkill(r.name, checked)}
                            />
                        )
                    },
                    {
                        title: '操作', key: 'action', width: 180,
                        render: (_, r) => (
                            <Space size="small">
                                <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openSkillDetail(r.name)}>
                                    查看
                                </Button>
                                <Popconfirm
                                    title={`卸载 Skill “${r.name}”？`}
                                    description="将从磁盘删除该 Skill 目录，不可恢复"
                                    okText="卸载"
                                    okButtonProps={{ danger: true }}
                                    cancelText="取消"
                                    onConfirm={() => uninstallSkill(r.name)}
                                >
                                    <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                                        卸载
                                    </Button>
                                </Popconfirm>
                            </Space>
                        )
                    },
                ]}
            />
        </Card>
    );

    const renderTools = () => (
        <Card
            title={
                <Space>
                    <CodeOutlined style={{ color: '#06b6d4' }} />
                    <span>MCP Tools</span>
                    <Tag color="cyan">{mcpTools.length} 个</Tag>
                </Space>
            }
            extra={
                <Input
                    prefix={<SearchOutlined />}
                    placeholder="搜索 Tool"
                    allowClear
                    value={toolKeyword}
                    onChange={e => setToolKeyword(e.target.value)}
                    style={{ width: 220 }}
                    size="small"
                />
            }
        >
            <Table
                dataSource={filteredTools}
                rowKey="name"
                size="middle"
                pagination={{ pageSize: 10, hideOnSinglePage: true }}
                columns={[
                    {
                        title: 'Tool', dataIndex: 'name', key: 'name', width: 220,
                        render: (text) => <Tag color="cyan">{text}</Tag>
                    },
                    {
                        title: '描述', dataIndex: 'description', key: 'desc',
                        render: (text) => <Text type="secondary">{text || '—'}</Text>
                    },
                ]}
            />
        </Card>
    );

    return (
        <PageContainer
            title="能力中心 (Capabilities)"
            description="统一查看 Agent 平台所有的 MCP Servers、Skills 与 Tools，及它们之间的拓扑关系。"
            actions={
                <Tooltip title="全部刷新">
                    <SyncOutlined spin={loading} onClick={fetchAll} style={{ fontSize: 18, cursor: 'pointer', color: '#a855f7' }} />
                </Tooltip>
            }
        >
            {/* 顶部统计 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={12} lg={6}>
                    <StatCard title="MCP Servers" value={`${connectedCount} / ${mcpStatus.length}`} icon={<ApiOutlined />} color="info" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title="Skills 已加载" value={`${activeSkillCount} / ${skills.length}`} icon={<ThunderboltOutlined />} color="primary" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title="可用 Tools" value={mcpTools.length} icon={<CodeOutlined />} color="success" />
                </Col>
                <Col xs={12} lg={6}>
                    <StatCard title="拓扑节点" value={topology.nodes.length} icon={<ApartmentOutlined />} color="warning" />
                </Col>
            </Row>

            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={[
                    {
                        key: 'topology',
                        label: <span><ApartmentOutlined /> 能力拓扑</span>,
                        children: renderTopology(),
                    },
                    {
                        key: 'mcp',
                        label: <span><ApiOutlined /> MCP Servers</span>,
                        children: renderMcpServers(),
                    },
                    {
                        key: 'skills',
                        label: <span><ThunderboltOutlined /> Skills</span>,
                        children: renderSkills(),
                    },
                    {
                        key: 'tools',
                        label: <span><CodeOutlined /> Tools</span>,
                        children: renderTools(),
                    },
                ]}
            />

            {/* Skill 安装 Modal */}
            <Modal
                title={<Space><UploadOutlined /> 安装 Skill 包</Space>}
                open={installOpen}
                onCancel={() => { setInstallOpen(false); setInstallFile(null); setInstallOverwrite(false); }}
                onOk={submitInstall}
                okText="安装"
                cancelText="取消"
                confirmLoading={installSubmitting}
                destroyOnHidden
            >
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                        上传一个 ZIP 包，里面应有<strong>一个顶层文件夹</strong>，包含 <code>SKILL.md</code>，
                        可选 <code>tools.py</code> 暴露工具。
                    </Paragraph>
                    <Upload.Dragger
                        accept=".zip,application/zip"
                        maxCount={1}
                        beforeUpload={() => false}
                        fileList={installFile ? [installFile] : []}
                        onChange={({ fileList }) => setInstallFile(fileList[fileList.length - 1] || null)}
                        onRemove={() => setInstallFile(null)}
                    >
                        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                        <p className="ant-upload-text">点击或拖拽 ZIP 文件到此区域</p>
                        <p className="ant-upload-hint">仅支持 .zip 格式</p>
                    </Upload.Dragger>
                    <Space>
                        <Switch checked={installOverwrite} onChange={setInstallOverwrite} />
                        <Text>覆盖同名 Skill（若已存在）</Text>
                    </Space>
                </Space>
            </Modal>

            {/* Skill 详情 Drawer */}
            <Drawer
                title={
                    <Space>
                        <ThunderboltOutlined style={{ color: '#a855f7' }} />
                        <span>{skillDetail?.name || '加载中…'}</span>
                        {skillDetail?.version && <Tag color="purple">v{skillDetail.version}</Tag>}
                    </Space>
                }
                width={720}
                open={skillDetailOpen}
                onClose={() => setSkillDetailOpen(false)}
                loading={skillDetailLoading}
            >
                {skillDetail && (
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        {skillDetail.summary && (
                            <Paragraph type="secondary">{skillDetail.summary}</Paragraph>
                        )}
                        {skillDetail.tags && skillDetail.tags.length > 0 && (
                            <Space wrap>
                                {skillDetail.tags.map(t => <Tag key={t} color="purple">{t}</Tag>)}
                            </Space>
                        )}
                        {skillDetail.tools && skillDetail.tools.length > 0 && (
                            <Card size="small" title={<Space><CodeOutlined /> Skill 内置工具</Space>}>
                                <Table
                                    dataSource={skillDetail.tools}
                                    rowKey="name"
                                    size="small"
                                    pagination={false}
                                    columns={[
                                        { title: '名称', dataIndex: 'name', render: (t) => <Tag color="cyan">{t}</Tag> },
                                        { title: '描述', dataIndex: 'description', render: (t) => <Text type="secondary">{t || '—'}</Text> },
                                    ]}
                                />
                            </Card>
                        )}
                        {skillDetail.body && (
                            <Card size="small" title="SKILL.md">
                                <div className="markdown-body" style={{ fontSize: 13 }}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{skillDetail.body}</ReactMarkdown>
                                </div>
                            </Card>
                        )}
                        {skillDetail.path && (
                            <Text type="secondary" style={{ fontSize: 11 }}>
                                <code>{skillDetail.path}</code>
                            </Text>
                        )}
                    </Space>
                )}
            </Drawer>

            {/* MCP Server 详情 Modal */}
            <Modal
                title={<Space><ApiOutlined /> MCP Server: {activeServer?.name}</Space>}
                open={serverModalOpen}
                onCancel={() => setServerModalOpen(false)}
                footer={null}
                width={600}
            >
                {activeServer && (
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        <Statistic title="状态" valueRender={() => (
                            <Badge status={activeServer.status === 'connected' ? 'success' : 'error'}
                                text={<Text strong>{activeServer.status.toUpperCase()}</Text>} />
                        )} />
                        <div>
                            <Text strong>Transport:</Text>
                            <Tag color="blue" style={{ marginLeft: 8 }}>{activeServer.type}</Tag>
                        </div>
                        <div>
                            <Text strong>启动命令:</Text>
                            <pre style={{
                                background: 'rgba(0,0,0,0.4)', padding: 12, borderRadius: 6,
                                marginTop: 8, fontSize: 12, color: '#06b6d4',
                            }}>
                                {activeServer.command} {activeServer.args.join(' ')}
                            </pre>
                        </div>
                        <div>
                            <Text strong>提供的 Tools (本 Server):</Text>
                            <div style={{ marginTop: 8 }}>
                                {/* 简化处理: 展示所有 mcpTools 作为可能来源 */}
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                    后端尚未按 server 分组返回 tools，请在 Tools Tab 中查看全量列表。
                                </Text>
                            </div>
                        </div>
                    </Space>
                )}
            </Modal>

            {/* MCP Server 添加/编辑 Modal */}
            <Modal
                title={<Space>{editMode === 'create' ? <PlusOutlined /> : <EditOutlined />} {editMode === 'create' ? '添加 MCP Server' : '编辑 MCP Server'}</Space>}
                open={editOpen}
                onCancel={() => setEditOpen(false)}
                onOk={submitServer}
                confirmLoading={editSubmitting}
                okText={editMode === 'create' ? '添加并连接' : '保存并重连'}
                width={580}
                destroyOnClose
            >
                <Form form={editForm} layout="vertical" preserve={false}>
                    <Form.Item
                        name="name"
                        label="Server 名称"
                        rules={[{ required: true, message: '请输入 server 名称' }]}
                        extra="唯一标识，建议小写英文，例如 filesystem / web-search"
                    >
                        <Input placeholder="filesystem" disabled={editMode === 'update'} />
                    </Form.Item>
                    <Form.Item name="type" label="Transport" initialValue="stdio">
                        <Input placeholder="stdio" />
                    </Form.Item>
                    <Form.Item
                        name="command"
                        label="启动命令"
                        rules={[{ required: true, message: '请输入启动命令' }]}
                        extra="可执行文件，例如 npx / python / node"
                    >
                        <Input placeholder="npx" />
                    </Form.Item>
                    <Form.Item
                        name="argsText"
                        label="启动参数 (空格分隔)"
                        extra="例如: -y @anthropic/mcp-filesystem /path/to/dir"
                    >
                        <Input.TextArea rows={3} placeholder="-y @anthropic/mcp-filesystem ./data" />
                    </Form.Item>
                    <Text type="warning" style={{ fontSize: 12 }}>
                        ⚠️ 保存后会立即重连所有 MCP Servers，期间正在执行的工具调用会被中断。
                    </Text>
                </Form>
            </Modal>
        </PageContainer>
    );
};
