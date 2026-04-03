import React, { useState, useEffect } from 'react';
import { App, Card, Input, Button, Select, Steps, Table, Typography, Tag, Space } from 'antd';
import { RocketOutlined, FileExcelOutlined, LoadingOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { knowledgeApi } from '../services/knowledgeApi';
import { generationApi } from '../services/generationApi';
import type { GenerateResponse } from '../services/generationApi';
import type { KnowledgeBase } from '../types';

const { TextArea } = Input;
import { useMonitor } from '../hooks/useMonitor';

const { Title, Text, Paragraph } = Typography;

export const StudioPage: React.FC = () => {
    const { track } = useMonitor();

    React.useEffect(() => {
        track('system', 'page_load', { page: 'Studio' });
    }, [track]);

    const { message } = App.useApp();
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [selectedKbs, setSelectedKbs] = useState<string[]>([]);
    const [task, setTask] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<GenerateResponse | null>(null);
    const [currentStep, setCurrentStep] = useState(0);

    useEffect(() => {
        loadKBs();
    }, []);

    const loadKBs = async () => {
        try {
            const response = await knowledgeApi.listKBs();
            setKbs(response.data.data);
        } catch {
            message.error("Failed to load Knowledge Bases");
        }
    };

    const handleGenerate = async () => {
        if (!task || selectedKbs.length === 0) {
            message.warning("Please enter a task and select at least one Knowledge Base");
            return;
        }

        setLoading(true);
        setResult(null);
        setCurrentStep(1); // Retrieve

        try {
            // Simulate steps for UX
            setTimeout(() => setCurrentStep(2), 1000); // Draft
            setTimeout(() => setCurrentStep(3), 2000); // Correct

            const res = await generationApi.run({
                task_description: task,
                kb_ids: selectedKbs
            });

            setCurrentStep(4); // Complete
            setResult(res);
            message.success("Generation Complete!");
        } catch (error: unknown) {
            console.error(error);
            message.error("Generation failed. Check console.");
            setCurrentStep(0);
        } finally {
            setLoading(false);
        }
    };

    const columns = result?.draft?.headers.map(h => ({
        title: h,
        dataIndex: h,
        key: h,
    })) || [];

    const stepItems = [
        { title: "Context Retrieval", description: "Hybrid Search + Reranking" },
        { title: "Active Drafting", description: "LLM Initial Design" },
        { title: "Self-Correction", description: "Critic Agent Review safety & constraints" },
        { title: "Artifact Export", description: "Format to Excel/CSV" }
    ];

    return (
        <PageContainer
            title="Creation Studio"
            description="Active Creating Agent — Generate structured artifacts (Docs, Plans, Specs) from Knowledge Base."
        >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <Card title="Task Configuration" bordered={false}>
                        <div style={{ marginBottom: 16 }}>
                            <Text strong>1. Select Knowledge Base(s)</Text>
                            <Select
                                mode="multiple"
                                style={{ width: '100%', marginTop: 8 }}
                                placeholder="Select KB Context"
                                value={selectedKbs}
                                onChange={setSelectedKbs}
                                options={kbs.map(kb => ({ label: kb.name, value: kb.id }))}
                            />
                        </div>

                        <div style={{ marginBottom: 16 }}>
                            <Text strong>2. Define Task</Text>
                            <TextArea
                                rows={6}
                                style={{ marginTop: 8 }}
                                placeholder="e.g. Generate a comprehensive Test Plan for the Login Module, covering positive, negative, and edge cases. Output as Excel."
                                value={task}
                                onChange={e => setTask(e.target.value)}
                            />
                        </div>

                        <Button
                            type="primary"
                            size="large"
                            icon={loading ? <LoadingOutlined /> : <RocketOutlined />}
                            onClick={handleGenerate}
                            loading={loading}
                            block
                        >
                            Start Generation
                        </Button>
                    </Card>

                    <Card title="Pipeline Status" bordered={false}>
                        <Steps direction="vertical" current={currentStep} size="small" items={stepItems} />

                        {result?.step_logs && (
                            <div style={{ marginTop: 16, background: 'var(--hm-color-bg-elevated)', padding: 8, borderRadius: 4, maxHeight: 200, overflowY: 'auto' }}>
                                <Text type="secondary" style={{ fontSize: 12, fontFamily: 'monospace' }}>
                                    {result.step_logs.map((log, i) => <div key={i}>{'>'} {log}</div>)}
                                </Text>
                            </div>
                        )}
                    </Card>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {result ? (
                        <Card
                            title={
                                <Space>
                                    <FileExcelOutlined style={{ color: 'green' }} />
                                    <span>Generated Artifact</span>
                                    {result.artifact_path && <Tag color="blue" variant="filled">{result.artifact_path}</Tag>}
                                </Space>
                            }
                            extra={<Button type="link">Download CSV</Button>}
                            bordered={false}
                            style={{ height: '100%' }}
                        >
                            <Table
                                dataSource={result.draft?.rows}
                                columns={columns}
                                pagination={false}
                                size="small"
                                scroll={{ x: true }}
                                rowKey={(_: unknown, index?: number) => index?.toString() || "0"}
                            />
                        </Card>
                    ) : (
                        <Card bordered={false} style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <div style={{ textAlign: 'center', color: 'var(--hm-color-text-secondary)' }}>
                                <RocketOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                                <Title level={4} style={{ color: 'var(--hm-color-text-muted)' }}>Ready to Create</Title>
                                <Text type="secondary">Configure and run a generation task to see results here.</Text>
                            </div>
                        </Card>
                    )}
                </div>
            </div>
        </PageContainer>
    );
};
