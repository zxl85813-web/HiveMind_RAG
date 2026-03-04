import React, { useState, useEffect } from 'react';
import { App, Button, Space, Table, Tag, Switch, Modal, Form, Input, Select, Checkbox, Card, Row, Col, Tabs, Typography, Tooltip, Divider } from 'antd';
import { LockOutlined, PlusOutlined, SafetyCertificateOutlined, AuditOutlined, HistoryOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer } from '../components/common';
import { securityApi } from '../services/securityApi';
import type { CreatePolicyParams } from '../services/securityApi';
import type { DesensitizationPolicy } from '../types';

const { Option } = Select;
const { TabPane } = Tabs;
const { Text } = Typography;

export const SecurityPage: React.FC = () => {
    const { message } = App.useApp();
    const { t } = useTranslation();
    const [policies, setPolicies] = useState<DesensitizationPolicy[]>([]);
    const [detectors, setDetectors] = useState<any[]>([]);
    const [auditLogs, setAuditLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [form] = Form.useForm();

    // ACL states
    const [aclDocId, setAclDocId] = useState('');
    const [aclPermissions, setAclPermissions] = useState<any[]>([]);
    const [aclLoading, setAclLoading] = useState(false);
    const [isAclModalOpen, setIsAclModalOpen] = useState(false);
    const [aclForm] = Form.useForm();

    const loadData = async () => {
        setLoading(true);
        try {
            const [policyRes, detectorRes, auditRes] = await Promise.all([
                securityApi.listPolicies(),
                securityApi.getDetectors(),
                securityApi.listAuditLogs(50)
            ]);
            setPolicies(policyRes.data.data);
            setDetectors(detectorRes.data.data.available_detectors);
            setAuditLogs(auditRes.data.data);
        } catch (error) {
            message.error(t('common.error'));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleActivate = async (id: number) => {
        try {
            await securityApi.activatePolicy(id);
            message.success(t('common.success'));
            loadData();
        } catch (e) {
            message.error(t('common.error'));
        }
    };

    const handleCreate = async () => {
        try {
            const values = await form.validateFields();

            // Convert actions to structured rules_json
            const rules: Record<string, any> = {};
            if (values.enabledDetectors) {
                values.enabledDetectors.forEach((dType: string) => {
                    const whitelistRaw = values[`whitelist_${dType}`] || '';
                    const whitelist = whitelistRaw.split('\n').map((s: string) => s.trim()).filter((s: string) => s.length > 0);

                    rules[dType] = {
                        action: values[`action_${dType}`] || 'mask',
                        severity: values[`severity_${dType}`] || 'medium',
                        whitelist: whitelist
                    };
                });
            }

            const payload: CreatePolicyParams = {
                name: values.name,
                description: values.description,
                is_active: true, // Auto activate new ones
                rules_json: JSON.stringify({
                    ...rules,
                    custom_regex: values.custom_regex || []
                })
            };

            await securityApi.createPolicy(payload);
            message.success(t('common.success'));
            setIsCreateModalOpen(false);
            form.resetFields();
            loadData();
        } catch (e) {
            console.error(e);
        }
    };

    const handleSearchAcl = async (val: string) => {
        const docId = val.trim();
        if (!docId) return;
        setAclDocId(docId);
        setAclLoading(true);
        try {
            const res = await securityApi.getDocumentPermissions(docId);
            setAclPermissions(res.data.data || []);
        } catch (e) {
            message.error("无法加载该文档的权限信息");
            setAclPermissions([]);
        } finally {
            setAclLoading(false);
        }
    };

    const handleRevokeAcl = async (id: string) => {
        try {
            await securityApi.revokePermission(id);
            message.success("已撤销权限");
            handleSearchAcl(aclDocId);
        } catch (e) {
            message.error("撤销失败");
        }
    };

    const handleGrantAcl = async () => {
        try {
            const values = await aclForm.validateFields();
            await securityApi.grantPermission({
                document_id: aclDocId,
                user_id: values.entity_type === 'user' ? values.entity_id : undefined,
                role_id: values.entity_type === 'role' ? values.entity_id : undefined,
                department_id: values.entity_type === 'department' ? values.entity_id : undefined,
                can_read: values.can_read,
                can_write: values.can_write
            });
            message.success("添加成功");
            setIsAclModalOpen(false);
            aclForm.resetFields();
            handleSearchAcl(aclDocId);
        } catch (e) {
            if (e && (e as any).errorFields) return; // form validation error
            message.error("添加失败");
        }
    };

    const columns = [
        {
            title: '策略名称',
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>,
        },
        {
            title: '描述',
            dataIndex: 'description',
            key: 'description',
        },
        {
            title: '规则概览',
            key: 'rules',
            render: (_: any, record: DesensitizationPolicy) => {
                let rules: any = {};
                try {
                    rules = JSON.parse(record.rules_json);
                } catch { }
                return (
                    <Space size={[0, 8]} wrap>
                        {Object.entries(rules).map(([k, v]: [string, any]) => {
                            const action = typeof v === 'string' ? v : v.action;
                            const severity = typeof v === 'string' ? 'medium' : v.severity;
                            const whitelistCount = (v.whitelist || []).length;
                            const color = severity === 'high' ? 'red' : severity === 'medium' ? 'orange' : 'blue';

                            return (
                                <Tooltip key={k} title={whitelistCount > 0 ? `白名单: ${v.whitelist.join(', ')}` : null}>
                                    <Tag color={color}>
                                        {k}: {action}
                                        {whitelistCount > 0 && <span style={{ opacity: 0.7, marginLeft: 4 }}>({whitelistCount}白)</span>}
                                    </Tag>
                                </Tooltip>
                            );
                        })}
                        {rules.custom_regex && rules.custom_regex.map((cr: any, idx: number) => (
                            <Tag key={`cr-${idx}`} color="cyan" icon={<LockOutlined />}>{cr.name}</Tag>
                        ))}
                    </Space>
                );
            }
        },
        {
            title: '状态',
            key: 'status',
            render: (_: any, record: DesensitizationPolicy) => (
                <Switch
                    checked={record.is_active}
                    onChange={() => handleActivate(record.id)}
                    checkedChildren="生效中"
                    unCheckedChildren="已停用"
                />
            )
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (text: string) => new Date(text).toLocaleString(),
        }
    ];

    const auditColumns = [
        {
            title: '时间',
            dataIndex: 'timestamp',
            key: 'time',
            width: 180,
            render: (t: string) => new Date(t).toLocaleString()
        },
        {
            title: '操作人',
            dataIndex: 'user_id',
            key: 'user',
            width: 150,
            render: (u: string) => <Tag icon={<LockOutlined />}>{u || 'SYSTEM'}</Tag>
        },
        {
            title: '动向',
            dataIndex: 'action',
            key: 'action',
            width: 150,
            render: (a: string) => <Tag color="blue">{a.toUpperCase()}</Tag>
        },
        {
            title: '资源类型',
            dataIndex: 'resource_type',
            key: 'res_type',
            width: 120
        },
        {
            title: '详情',
            dataIndex: 'details',
            key: 'details',
            ellipsis: true,
            render: (d: string) => <Text type="secondary" style={{ fontSize: '12px' }}>{d}</Text>
        }
    ];

    return (
        <PageContainer
            title="安全与治理中心"
            description="统一管控数据脱敏、权限访问控制 (ACL) 及安全审计流水。"
            actions={
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
                    新建脱敏策略
                </Button>
            }
        >
            <Tabs defaultActiveKey="policies">
                <TabPane tab={<span><SafetyCertificateOutlined /> 数据脱敏策略</span>} key="policies">
                    <Row gutter={[16, 16]}>
                        <Col span={24}>
                            <Card title="脱敏策略管理" bordered={false}>
                                <Table
                                    columns={columns}
                                    dataSource={policies}
                                    rowKey="id"
                                    loading={loading}
                                    pagination={false}
                                />
                            </Card>
                        </Col>
                        <Col span={24}>
                            <Card title="原生敏感项检测器" bordered={false}>
                                <Space size={[0, 8]} wrap>
                                    {detectors.map(d => (
                                        <Tag key={d.type} color="blue">{d.type} - {d.description.trim()}</Tag>
                                    ))}
                                </Space>
                            </Card>
                        </Col>
                    </Row>
                </TabPane>

                <TabPane tab={<span><HistoryOutlined /> 安全审计日志 (Audit)</span>} key="audit">
                    <Card title="全系统安全事件追踪" bordered={false}>
                        <Table
                            columns={auditColumns}
                            dataSource={auditLogs}
                            rowKey="id"
                            loading={loading}
                            pagination={{ pageSize: 15 }}
                            locale={{ emptyText: "暂无审计记录" }}
                        />
                    </Card>
                </TabPane>

                <TabPane tab={<span><AuditOutlined /> 权限访问控制 (ACL)</span>} key="acl">
                    <Card title="文档级权限概览" bordered={false}>
                        <Text type="secondary">在此可以管理基于用户、角色或部门的文档访问权限。Admin 拥有所有文档的读写权。</Text>
                        <div style={{ marginTop: 24, marginBottom: 16 }}>
                            <Input.Search
                                placeholder="输入文档 ID 查询权限设置"
                                onSearch={handleSearchAcl}
                                enterButton
                                style={{ maxWidth: 400 }}
                            />
                        </div>
                        {aclDocId && (
                            <>
                                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Text strong>当前编辑文档: <Tag>{aclDocId}</Tag></Text>
                                    <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setIsAclModalOpen(true)}>添加鉴权规则</Button>
                                </div>
                                <Table
                                    dataSource={aclPermissions}
                                    loading={aclLoading}
                                    rowKey="id"
                                    columns={[
                                        {
                                            title: '目标实体',
                                            render: (_: any, r: any) => {
                                                if (r.user_id) return <Tag color="blue">用户: {r.user_id}</Tag>;
                                                if (r.role_id) return <Tag color="green">角色: {r.role_id}</Tag>;
                                                if (r.department_id) return <Tag color="orange">部门: {r.department_id}</Tag>;
                                                return <Tag>未知实体</Tag>;
                                            }
                                        },
                                        {
                                            title: '权限',
                                            key: 'perms',
                                            render: (_: any, r: any) => (
                                                <Space>
                                                    <Tag color={r.can_read ? 'success' : 'default'}>读取</Tag>
                                                    <Tag color={r.can_write ? 'success' : 'default'}>写入 / 修改</Tag>
                                                </Space>
                                            )
                                        },
                                        {
                                            title: '添加时间',
                                            dataIndex: 'created_at',
                                            key: 'created_at',
                                            render: (t: string) => <Text type="secondary">{new Date(t).toLocaleString()}</Text>
                                        },
                                        {
                                            title: '操作',
                                            key: 'action',
                                            render: (_: any, r: any) => (
                                                <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => handleRevokeAcl(r.id)}>移除</Button>
                                            )
                                        }
                                    ]}
                                    pagination={false}
                                    locale={{ emptyText: "当前文档暂无特殊权限规则 (继承默认权限)" }}
                                />
                            </>
                        )}
                    </Card>
                </TabPane>
            </Tabs>

            <Modal
                title="新建脱敏策略"
                open={isCreateModalOpen}
                onOk={handleCreate}
                onCancel={() => setIsCreateModalOpen(false)}
                width={600}
                destroyOnClose
            >
                <Form form={form} layout="vertical">
                    <Form.Item name="name" label="策略名称" rules={[{ required: true }]}>
                        <Input placeholder="输入策略名称，例如：严格全局脱敏" />
                    </Form.Item>
                    <Form.Item name="description" label="描述">
                        <Input.TextArea placeholder="该策略的用途说明" />
                    </Form.Item>

                    <Form.Item name="enabledDetectors" label="启用检测器配置">
                        <Checkbox.Group style={{ width: '100%' }}>
                            <Row gutter={[8, 12]}>
                                {detectors.map(d => (
                                    <Col span={24} key={d.type}>
                                        <Card size="small" type="inner" styles={{ body: { padding: '12px' } }}>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                                                <Checkbox value={d.type} style={{ fontWeight: 500 }}>
                                                    {d.type.toUpperCase()} <Text type="secondary" style={{ fontSize: 11, fontWeight: 400 }}>({d.description.trim()})</Text>
                                                </Checkbox>
                                                <Space>
                                                    <Form.Item name={`severity_${d.type}`} noStyle initialValue="medium">
                                                        <Select style={{ width: 85 }} size="small" placeholder="风险">
                                                            <Option value="high">高风险</Option>
                                                            <Option value="medium">中</Option>
                                                            <Option value="low">低</Option>
                                                        </Select>
                                                    </Form.Item>
                                                    <Form.Item name={`action_${d.type}`} noStyle initialValue="mask">
                                                        <Select style={{ width: 100 }} size="small">
                                                            <Option value="mask">掩码</Option>
                                                            <Option value="star">全星号</Option>
                                                            <Option value="hash">哈希</Option>
                                                            <Option value="placeholder">占位符</Option>
                                                            <Option value="delete">彻底删除</Option>
                                                        </Select>
                                                    </Form.Item>
                                                </Space>
                                            </div>
                                            <Form.Item
                                                name={`whitelist_${d.type}`}
                                                style={{ marginBottom: 0 }}
                                            >
                                                <Input.TextArea
                                                    autoSize={{ minRows: 1, maxRows: 3 }}
                                                    placeholder="例外白名单 (每行一个)..."
                                                    style={{ fontSize: 11, background: 'rgba(0,0,0,0.02)' }}
                                                />
                                            </Form.Item>
                                        </Card>
                                    </Col>
                                ))}
                            </Row>
                        </Checkbox.Group>
                    </Form.Item>

                    <Divider orientation={"left" as any} style={{ fontSize: 13 }}>自定义正则规则 (高级)</Divider>
                    <p style={{ fontSize: 11, color: '#8c8c8c', marginBottom: 16 }}>
                        使用标准 Python 正则表达式。例如 <code>SECRET-\d+</code>。支持捕获组。
                    </p>
                    <Form.List name="custom_regex">
                        {(fields, { add, remove }) => (
                            <>
                                {fields.map(({ key, name, ...restField }) => (
                                    <Card
                                        key={key}
                                        size="small"
                                        style={{ marginBottom: 12, background: 'rgba(24, 144, 255, 0.02)' }}
                                        extra={<DeleteOutlined onClick={() => remove(name)} style={{ color: '#ff4d4f' }} />}
                                        title={<span style={{ fontSize: 12 }}>自定义规则 #{name + 1}</span>}
                                    >
                                        <Row gutter={8}>
                                            <Col span={10}>
                                                <Form.Item {...restField} name={[name, 'name']} label="规则标识" rules={[{ required: true }]}>
                                                    <Input placeholder="SECRET_ID" size="small" />
                                                </Form.Item>
                                            </Col>
                                            <Col span={14}>
                                                <Form.Item {...restField} name={[name, 'pattern']} label="正则模式" rules={[{ required: true }]}>
                                                    <Input placeholder="SECRET-\d{4}" size="small" />
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item {...restField} name={[name, 'action']} label="脱敏动作" initialValue="mask">
                                                    <Select size="small">
                                                        <Option value="mask">掩码</Option>
                                                        <Option value="star">全星号</Option>
                                                        <Option value="delete">彻底删除</Option>
                                                    </Select>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item {...restField} name={[name, 'severity']} label="风险等级" initialValue="medium">
                                                    <Select size="small">
                                                        <Option value="high">高</Option>
                                                        <Option value="medium">中</Option>
                                                        <Option value="low">低</Option>
                                                    </Select>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                    </Card>
                                ))}
                                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />} size="small">
                                    添加自定义正则检测
                                </Button>
                            </>
                        )}
                    </Form.List>
                </Form>
            </Modal>

            <Modal
                title="添加权限规则"
                open={isAclModalOpen}
                onOk={handleGrantAcl}
                onCancel={() => setIsAclModalOpen(false)}
                destroyOnClose
            >
                <Form form={aclForm} layout="vertical" initialValues={{ entity_type: 'user', can_read: true, can_write: false }}>
                    <Form.Item name="entity_type" label="授权类型" rules={[{ required: true }]}>
                        <Select>
                            <Option value="user">指定用户 (User)</Option>
                            <Option value="role">角色组 (Role)</Option>
                            <Option value="department">所属部门 (Department)</Option>
                        </Select>
                    </Form.Item>
                    <Form.Item name="entity_id" label="实体 ID" rules={[{ required: true, message: '请输入目标 ID' }]}>
                        <Input placeholder="输入目标 ID (例: 10015)" />
                    </Form.Item>
                    <Form.Item name="can_read" valuePropName="checked">
                        <Checkbox>允许读取资源 (Read)</Checkbox>
                    </Form.Item>
                    <Form.Item name="can_write" valuePropName="checked">
                        <Checkbox>允许修改/删除资源 (Write)</Checkbox>
                    </Form.Item>
                </Form>
            </Modal>
        </PageContainer >
    );
};
