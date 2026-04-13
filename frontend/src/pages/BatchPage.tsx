import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Progress, Modal, Space, App as AntApp, Typography, Collapse } from 'antd';
import { PlayCircleOutlined, StopOutlined, SyncOutlined, EyeOutlined } from '@ant-design/icons';
import { PageContainer, PermissionButton } from '../components/common';
import { batchApi, type BatchJob, type TaskUnit } from '../services/batchApi';
import { useAuthStore } from '../stores/authStore';
import { useMonitor } from '../hooks/useMonitor';

const { Text } = Typography;
const { Panel } = Collapse;

export const BatchPage: React.FC = () => {
    const hasAccess = useAuthStore((state) => state.hasAccess);
    const { track } = useMonitor();
    const { notification } = AntApp.useApp();
    
    useEffect(() => {
        track('system', 'page_load', { page: 'BatchJobs' });
    }, [track]);

    const [jobs, setJobs] = useState<BatchJob[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedJob, setSelectedJob] = useState<BatchJob | null>(null);
    const [modalVisible, setModalVisible] = useState(false);

    const fetchJobs = async () => {
        setLoading(true);
        try {
            const res = await batchApi.getJobs();
            // Mock returns { success, data: [...], message }, axios wraps in res.data
            const rawData = res.data as any;
            const jobsData = rawData?.data ?? rawData;
            if (Array.isArray(jobsData)) {
                setJobs(jobsData);
            }
        } catch {
            notification.error({ title: 'Error loading batch jobs' });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 5000); // Polling every 5 seconds
        return () => clearInterval(interval);
    }, []);

    const handleCreateMockJob = async () => {
        if (!hasAccess({ anyPermissions: ['batch:operate'] })) {
            notification.warning({ title: '当前账号没有创建批处理任务权限' });
            return;
        }

        try {
            await batchApi.createJob({
                name: "Demo Analytics Pipeline",
                description: "This is a demo pipeline created from the frontend",
                max_concurrency: 2,
                tasks: [
                    { id: "task_a", name: "Data Extraction", input_data: { prompt: "Extract key metrics" } },
                    { id: "task_b", name: "Image Analysis", input_data: { prompt: "Analyze visualization" } },
                    { id: "task_c", name: "Report Generation", depends_on: ["task_a", "task_b"], input_data: { prompt: "Generate full summary" } }
                ]
            });
            notification.success({ title: 'Demo Job Created successfully!' });
            fetchJobs();
        } catch {
            notification.error({ title: 'Failed to create mock job' });
        }
    };

    const handleCancelJob = async (jobId: string) => {
        if (!hasAccess({ anyPermissions: ['batch:operate'] })) {
            notification.warning({ message: '当前账号没有取消批处理任务权限' });
            return;
        }

        try {
            await batchApi.cancelJob(jobId);
            notification.success({ title: `Job ${jobId} cancelled` });
            fetchJobs();
        } catch {
            notification.error({ title: 'Failed to cancel job' });
        }
    };

    const StatusTag = ({ status }: { status: string }) => {
        let color = 'default';
        if (['success', 'completed'].includes(status)) color = 'success';
        if (['failed', 'error', 'cancelled'].includes(status)) color = 'error';
        if (['running', 'queued'].includes(status)) color = 'processing';
        return <Tag color={color}>{status.toUpperCase()}</Tag>;
    };

    const columns = [
        {
            title: 'Job Name',
            dataIndex: 'name',
            key: 'name',
            render: (text: string, record: BatchJob) => (
                <div>
                    <Text strong>{text}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>{record.id}</Text>
                </div>
            )
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => <StatusTag status={status} />
        },
        {
            title: 'Progress',
            key: 'progress',
            render: (_: unknown, record: BatchJob) => {
                const percent = Math.floor(record.success_rate * 100);
                return <Progress percent={percent} size="small" />;
            }
        },
        {
            title: 'Tasks',
            key: 'tasks',
            render: (_: unknown, record: BatchJob) => (
                <Text>{Object.keys(record.tasks).length} Total</Text>
            )
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_: unknown, record: BatchJob) => (
                <Space>
                    <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => { setSelectedJob(record); setModalVisible(true); }}
                    />
                    {record.status === 'running' && (
                        <PermissionButton
                            danger
                            size="small"
                            icon={<StopOutlined />}
                            onClick={() => handleCancelJob(record.id)}
                            access={{ anyPermissions: ['batch:operate'] }}
                        />
                    )}
                </Space>
            )
        }
    ];

    const taskColumns = [
        { title: 'Task Name', dataIndex: 'name', key: 'name' },
        { title: 'Status', dataIndex: 'status', key: 'status', render: (status: string) => <StatusTag status={status} /> },
        { title: 'Duration (s)', key: 'duration', render: (_: unknown, record: TaskUnit) => record.duration_seconds?.toFixed(2) || '-' }
    ];

    return (
        <PageContainer
            title="Batch Jobs & Workflows"
            description="Monitor and manage background processing pipelines."
            maxWidth={1000}
        >
            <Card
                title={<span><SyncOutlined spin={loading} /> Workflow Manager</span>}
                extra={
                    <PermissionButton
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={handleCreateMockJob}
                        access={{ anyPermissions: ['batch:operate'] }}
                    >
                        Create Demo Pipeline
                    </PermissionButton>
                }
            >
                <Table
                    columns={columns}
                    dataSource={jobs}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            <Modal
                title={`Job Details: ${selectedJob?.name}`}
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                footer={null}
                width={800}
            >
                {selectedJob && (
                    <>
                        <div style={{ marginBottom: 16 }}>
                            <Text strong>Status: </Text> <StatusTag status={selectedJob.status} />
                            <Text strong style={{ marginLeft: 16 }}>Created By: </Text> <Text code>{selectedJob.id}</Text>
                        </div>
                        <Table
                            size="small"
                            columns={taskColumns}
                            dataSource={Object.values(selectedJob.tasks)}
                            rowKey="id"
                            pagination={false}
                        />
                        <Collapse style={{ marginTop: 16 }}>
                            <Panel header="Raw Job Data" key="1">
                                <pre style={{ maxHeight: 300, overflow: 'auto', fontSize: '12px' }}>
                                    {JSON.stringify(selectedJob, null, 2)}
                                </pre>
                            </Panel>
                        </Collapse>
                    </>
                )}
            </Modal>
        </PageContainer>
    );
};
