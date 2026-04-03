import React, { useState, useEffect } from 'react';
import { Table, Tag, Space, Card, App, Empty, Typography } from 'antd';
import { DeleteOutlined, ExportOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { PermissionButton } from '../components/common';
import { ftApi } from '../services/ftApi';
import type { FineTuningItem } from '../types';
import { useAuthStore } from '../stores/authStore';
import { useMonitor } from '../hooks/useMonitor';

const { Text } = Typography;

export const FineTuningPage: React.FC = () => {
    const { track } = useMonitor();

    useEffect(() => {
        track('system', 'page_load', { page: 'FineTuningManager' });
    }, [track]);

    const { message, modal } = App.useApp();
    const hasAccess = useAuthStore((state) => state.hasAccess);
    const [items, setItems] = useState<FineTuningItem[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await ftApi.getItems();
            setItems(res.data.data);
        } catch {
            message.error("加载失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleDelete = (id: string) => {
        if (!hasAccess({ anyPermissions: ['finetuning:manage'] })) {
            message.warning('当前账号没有微调数据管理权限');
            return;
        }

        modal.confirm({
            title: '确认删除?',
            content: '删除后无法恢复该微调用例。',
            onOk: async () => {
                try {
                    await ftApi.deleteItem(id);
                    message.success("已删除");
                    fetchData();
                } catch {
                    message.error("删除失败");
                }
            }
        });
    };

    const columns = [
        {
            title: '指令 (Instruction)',
            dataIndex: 'instruction',
            key: 'instruction',
            render: (text: string) => <Text ellipsis={{ tooltip: text }}>{text}</Text>
        },
        {
            title: '标准回答',
            dataIndex: 'output',
            key: 'output',
            render: (text: string) => <Text ellipsis={{ tooltip: text }}>{text}</Text>
        },
        {
            title: '来源',
            dataIndex: 'source_type',
            key: 'source',
            render: (s: string) => {
                const sourceConfig: Record<string, { text: string, color: string }> = {
                    manual: { text: '手动输入', color: 'blue' },
                    evaluation_correction: { text: '评估修正', color: 'purple' },
                    user_feedback: { text: '用户反馈', color: 'orange' }
                };
                const config = sourceConfig[s] || { text: s, color: 'default' };
                return <Tag color={config.color}>{config.text}</Tag>;
            }
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (s: string) => {
                if (s === 'verified') return <Tag icon={<CheckCircleOutlined />} color="success">已确认</Tag>;
                if (s === 'bad_case') return <Tag icon={<ClockCircleOutlined />} color="warning">待修正 (Bad Case)</Tag>;
                return <Tag color="default">{s}</Tag>;
            }
        },
        {
            title: '操作',
            key: 'action',
            render: (_: unknown, record: FineTuningItem) => (
                <Space>
                    <PermissionButton
                        size="small"
                        icon={<ExportOutlined />}
                        access={{ anyPermissions: ['finetuning:manage'] }}
                    >
                        修改
                    </PermissionButton>
                    <PermissionButton
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(record.id)}
                        access={{ anyPermissions: ['finetuning:manage'] }}
                    />
                </Space>
            )
        }
    ];

    const handleExportDataset = () => {
        if (!hasAccess({ anyPermissions: ['finetuning:manage'] })) {
            message.warning('当前账号没有导出微调数据权限');
            return;
        }

        message.info('导出能力将在后续版本接入真实后端下载接口');
    };

    return (
        <PageContainer
            title="微调数据集管理"
            description="收集并管理高质量的 QA 对，用于后续模型 SFT (监督微调) 训练。"
            actions={
                <PermissionButton
                    type="primary"
                    icon={<ExportOutlined />}
                    onClick={handleExportDataset}
                    access={{ anyPermissions: ['finetuning:manage'] }}
                >
                    导出数据集 (JSONL)
                </PermissionButton>
            }
        >
            <Card styles={{ body: { padding: 0 } }}>
                <Table
                    dataSource={items}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                    locale={{ emptyText: <Empty description="暂无微调数据，可从评估反馈中加入" /> }}
                />
            </Card>
        </PageContainer>
    );
};
