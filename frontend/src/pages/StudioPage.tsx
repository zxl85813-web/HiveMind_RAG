import React, { useState, useEffect } from 'react';
import { App, Card, Input, Button, Select, Steps, Table, Typography, Tag, Space } from 'antd';
import { RocketOutlined, FileExcelOutlined, LoadingOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { knowledgeApi } from '../services/knowledgeApi';
import { generationApi } from '../services/generationApi';
import type { GenerateResponse } from '../services/generationApi';
import type { KnowledgeBase } from '../types';

const { TextArea } = Input;
const { Title, Text } = Typography;

export const StudioPage: React.FC = () => {
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
        } catch (error) {
            message.error("加载知识库失败，请检查网络连接");
        }
    };

    const handleGenerate = async () => {
        if (!task || selectedKbs.length === 0) {
            message.warning("请在左侧输入任务描述并选择至少一个关联知识库");
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
            message.success("资产创作与生成已顺利完成！");
        } catch (error) {
            console.error(error);
            message.error("资产生成失败，请检查控制台。");
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
        { title: "上下文检索", description: "混合检索与重排过滤 (Hybrid Search + Reranking)" },
        { title: "智能草案设计", description: "大模型初稿生成 (LLM Initial Design)" },
        { title: "自动化反思纠错", description: "评判智能体自查合规性与约束约束 (Self-Correction)" },
        { title: "资产格式化导出", description: "转换并导出为 Excel/CSV 格式" }
    ];

    return (
        <PageContainer
            title="智能创作空间 (Creation Studio)"
            description="基于您选择的知识库和输入任务描述，自动化生成高契合度的结构化文档、设计方案与规格说明书。"
        >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <Card title="任务配置" bordered={false}>
                        <div style={{ marginBottom: 16 }}>
                            <Text strong>1. 选择关联知识库</Text>
                            <Select
                                mode="multiple"
                                style={{ width: '100%', marginTop: 8 }}
                                placeholder="请选择关联知识库上下文"
                                value={selectedKbs}
                                onChange={setSelectedKbs}
                                options={kbs.map(kb => ({ label: kb.name, value: kb.id }))}
                            />
                        </div>

                        <div style={{ marginBottom: 16 }}>
                            <Text strong>2. 明确生成任务</Text>
                            <TextArea
                                rows={6}
                                style={{ marginTop: 8 }}
                                placeholder="例如：针对登录模块，生成一份包含正常、异常和边界用例的全面测试计划，并以 Excel 格式输出。"
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
                            开始智能创作
                        </Button>
                    </Card>

                    <Card title="执行流水线状态" bordered={false}>
                        <Steps direction="vertical" current={currentStep} size="small" items={stepItems} />

                        {result?.step_logs && (
                            <div style={{ marginTop: 16, background: '#1f1f1f', padding: 8, borderRadius: 4, maxHeight: 200, overflowY: 'auto' }}>
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
                                    <span>已生成的资产文件</span>
                                    {result.artifact_path && <Tag color="blue" variant="filled">{result.artifact_path}</Tag>}
                                </Space>
                            }
                            extra={<Button type="link">下载 CSV 格式</Button>}
                            bordered={false}
                            style={{ height: '100%' }}
                        >
                            <Table
                                dataSource={result.draft?.rows}
                                columns={columns}
                                pagination={false}
                                size="small"
                                scroll={{ x: true }}
                                rowKey={(_, index) => index?.toString() || "0"}
                            />
                        </Card>
                    ) : (
                        <Card bordered={false} style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <div style={{ textAlign: 'center', color: '#ccc' }}>
                                <RocketOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                                <Title level={4} style={{ color: '#555' }}>创作中心已就绪</Title>
                                <Text type="secondary">在左侧配置关联知识库并输入任务要求，生成的资产数据将在这里呈现。</Text>
                            </div>
                        </Card>
                    )}
                </div>
            </div>
        </PageContainer>
    );
};
