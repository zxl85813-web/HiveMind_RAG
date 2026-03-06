import React, { useState, useEffect } from 'react';
import { Modal, Table, Button, Form, Input, Switch, Select, message, Typography } from 'antd';
import { DeleteOutlined, UserAddOutlined } from '@ant-design/icons';
import { knowledgeApi } from '../../services/knowledgeApi';
import type { KnowledgeBasePermission } from '../../types';

const { Text } = Typography;
const { Option } = Select;

interface Props {
    kbId: string;
    open: boolean;
    onClose: () => void;
}

export const KBPermissionsModal: React.FC<Props> = ({ kbId, open, onClose }) => {
    const [permissions, setPermissions] = useState<KnowledgeBasePermission[]>([]);
    const [loading, setLoading] = useState(false);
    const [form] = Form.useForm();
    const [adding, setAdding] = useState(false);

    useEffect(() => {
        if (open && kbId) {
            loadPermissions();
            form.resetFields();
            form.setFieldsValue({ can_read: true, can_write: false, can_manage: false });
        }
    }, [open, kbId]);

    const loadPermissions = async () => {
        setLoading(true);
        try {
            const res = await knowledgeApi.getPermissions(kbId);
            setPermissions(res.data.data);
        } catch (e: any) {
            if (e.response?.status !== 403) {
                message.error('Failed to load permissions');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (values: any) => {
        if (!values.user_id && !values.department_id && !values.role_id) {
            message.error('Please specify at least a User ID, Role ID, or Department ID');
            return;
        }
        setAdding(true);
        try {
            await knowledgeApi.addPermission(kbId, values);
            message.success('Permission added successfully');
            form.resetFields();
            form.setFieldsValue({ can_read: true, can_write: false, can_manage: false });
            loadPermissions();
        } catch (e: any) {
            message.error(e.response?.data?.message || 'Failed to add permission');
        } finally {
            setAdding(false);
        }
    };

    const handleDelete = async (permId: string) => {
        try {
            await knowledgeApi.deletePermission(kbId, permId);
            message.success('Permission removed');
            loadPermissions();
        } catch (e: any) {
            message.error(e.response?.data?.message || 'Failed to remove permission');
        }
    };

    const columns = [
        {
            title: 'Target',
            key: 'target',
            render: (_: any, record: KnowledgeBasePermission) => {
                if (record.user_id) return <Text strong>User: {record.user_id}</Text>;
                if (record.role_id) return <Text strong>Role: {record.role_id}</Text>;
                if (record.department_id) return <Text strong>Dept: {record.department_id}</Text>;
                return <Text>Unknown</Text>;
            }
        },
        {
            title: 'Read',
            dataIndex: 'can_read',
            render: (val: boolean) => val ? <Text type="success">Yes</Text> : <Text type="secondary">No</Text>
        },
        {
            title: 'Write',
            dataIndex: 'can_write',
            render: (val: boolean) => val ? <Text type="success">Yes</Text> : <Text type="secondary">No</Text>
        },
        {
            title: 'Manage',
            dataIndex: 'can_manage',
            render: (val: boolean) => val ? <Text type="success">Yes</Text> : <Text type="secondary">No</Text>
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_: any, record: KnowledgeBasePermission) => (
                <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDelete(record.id)}
                />
            )
        }
    ];

    return (
        <Modal
            title="Knowledge Base Permissions (ACL)"
            open={open}
            onCancel={onClose}
            footer={null}
            width={700}
        >
            <div style={{ marginBottom: 24, padding: 16, background: 'rgba(255,255,255,0.02)', borderRadius: 8 }}>
                <Text strong style={{ display: 'block', marginBottom: 16 }}>Add New Permission Rule</Text>
                <Form
                    form={form}
                    layout="inline"
                    onFinish={handleAdd}
                >
                    <Form.Item name="target_type" initialValue="user_id">
                        <Select style={{ width: 120 }}>
                            <Option value="user_id">User ID</Option>
                            <Option value="department_id">Department ID</Option>
                            <Option value="role_id">Role ID</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => prevValues.target_type !== currentValues.target_type}
                    >
                        {({ getFieldValue }) => {
                            const targetType = getFieldValue('target_type') || 'user_id';
                            return (
                                <Form.Item name={targetType} rules={[{ required: true, message: 'ID is required' }]}>
                                    <Input placeholder={`Enter ${targetType.split('_')[0]} ID`} style={{ width: 150 }} />
                                </Form.Item>
                            );
                        }}
                    </Form.Item>

                    <Form.Item name="can_read" valuePropName="checked">
                        <Switch checkedChildren="Read" unCheckedChildren="No Read" />
                    </Form.Item>
                    <Form.Item name="can_write" valuePropName="checked">
                        <Switch checkedChildren="Write" unCheckedChildren="No Write" />
                    </Form.Item>
                    <Form.Item name="can_manage" valuePropName="checked">
                        <Switch checkedChildren="Manage" unCheckedChildren="No Manage" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={adding} icon={<UserAddOutlined />}>
                            Add
                        </Button>
                    </Form.Item>
                </Form>
            </div>

            <Table
                dataSource={permissions}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={false}
                size="small"
            />
        </Modal>
    );
};
