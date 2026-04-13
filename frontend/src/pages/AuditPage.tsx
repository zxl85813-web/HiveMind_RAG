import React, { useState, useEffect } from 'react';
import { Table, Tag, Button, Space, Typography, Card, Progress, App, Empty, Tooltip, Drawer, Flex, theme } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, SafetyCertificateOutlined, EyeOutlined, SearchOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { auditApi } from '../services/auditApi';
import { knowledgeApi } from '../services/knowledgeApi';
import type { DocumentReview } from '../types';
import { useMonitor } from '../hooks/useMonitor';


const { Title, Text } = Typography;

export const AuditPage: React.FC = () => {
    const { track } = useMonitor();
    
    React.useEffect(() => {
        track('system', 'page_load', { page: 'AuditLog' });
    }, [track]);
    const { message } = App.useApp();
    const { token } = theme.useToken();
    const [reviews, setReviews] = useState<DocumentReview[]>([]);
    const [loading, setLoading] = useState(false);

    // Preview state
    const [previewDocId, setPreviewDocId] = useState<string | null>(null);
    const [previewContent, setPreviewContent] = useState<string>('');
    const [previewLoading, setPreviewLoading] = useState(false);
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);

    const fetchQueue = async () => {
        setLoading(true);
        try {
            const res = await auditApi.getQueue();
            setReviews(res.data.data);
        } catch {
            message.error("无法加载审核队列");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchQueue();
    }, []);

    const handleApprove = async (id: string) => {
        try {
            await auditApi.approve(id);
            message.success("审核已通过");
            fetchQueue();
        } catch {
            message.error("操作失败");
        }
    };

    const handleReject = async (id: string) => {
        try {
            await auditApi.reject(id);
            message.success("已完成驳回操作");
            fetchQueue();
        } catch {
            message.error("操作失败");
        }
    };

    const handlePreview = async (docId: string) => {
        setPreviewDocId(docId);
        setIsPreviewOpen(true);
        setPreviewLoading(true);
        setPreviewContent('');
        try {
            const res = await knowledgeApi.getDocumentPreview(docId);
            setPreviewContent(res.data.data.text);
        } catch (err: unknown) {
            const error = err as any;
            setPreviewContent(error.response?.data?.message || error.message || "无法加载文档预览内容");
        } finally {
            setPreviewLoading(false);
        }
    };

    const columns = [
        {
            title: '文档 ID',
            dataIndex: 'document_id',
            key: 'doc_id',
            width: 120,
            render: (docId: string) => (
                <Space>
                    <SearchOutlined style={{ color: token.colorInfo, opacity: 0.6 }} />
                    <a onClick={() => handlePreview(docId)} style={{ fontWeight: 500 }}>
                        {docId.substring(0, 8)}
                    </a>
                </Space>
            )
        },
        {
            title: '质量评分',
            dataIndex: 'quality_score',
            key: 'score',
            width: 150,
            render: (score: number) => {
                let color = token.colorError;
                if (score >= 0.8) color = token.colorSuccess;
                else if (score >= 0.4) color = token.colorWarning;
                return (
                    <div style={{ padding: '4px 0' }}>
                        <Flex justify="space-between" align="center" style={{ marginBottom: 4 }}>
                            <Text style={{ fontSize: '13px', fontWeight: 600, color }}>{(score * 100).toFixed(0)}%</Text>
                            <Text type="secondary" style={{ fontSize: '11px' }}>{score.toFixed(2)}</Text>
                        </Flex>
                        <Progress
                            percent={Math.round(score * 100)}
                            size="small"
                            strokeColor={color}
                            showInfo={false}
                            style={{ margin: 0 }}
                        />
                    </div>
                );
            }
        },
        {
            title: '质检详情',
            key: 'details',
            render: (_: unknown, record: DocumentReview) => (
                <Flex wrap="wrap" gap={6} style={{ padding: '4px 0' }}>
                    <Tag bordered={false} color={record.content_length_ok ? 'success' : 'error'} style={{ margin: 0 }}>
                        长度: {record.content_length_ok ? 'OK' : '过短'}
                    </Tag>
                    <Tag bordered={false} color={record.duplicate_ratio < 0.3 ? 'success' : 'warning'} style={{ margin: 0 }}>
                        重复率: {(record.duplicate_ratio * 100).toFixed(0)}%
                    </Tag>
                    <Tag bordered={false} color={record.garble_ratio < 0.05 ? 'success' : 'error'} style={{ margin: 0 }}>
                        乱码率: {(record.garble_ratio * 100).toFixed(0)}%
                    </Tag>
                    <Tag bordered={false} color={record.format_integrity_ok !== false ? 'success' : 'error'} style={{ margin: 0 }}>
                        格式: {record.format_integrity_ok !== false ? '完整' : '缺失'}
                    </Tag>
                    {record.pii_count !== undefined && record.pii_count > 0 && (
                        <Tag bordered={false} color={record.pii_count > 5 ? 'error' : 'blue'} style={{ margin: 0 }}>
                            敏感项: {record.pii_count}
                        </Tag>
                    )}
                    {(record.overlap_score || 0) > 0 && (
                        <Tooltip title="知识重叠度评估。分值越高，模型已知的内容越多，增量价值越低。">
                            <Tag
                                bordered={false}
                                color={(record.overlap_score || 0) < 0.5 ? 'processing' : 'warning'}
                                icon={<SafetyCertificateOutlined />}
                                style={{ margin: 0 }}
                            >
                                知识重叠: {((record.overlap_score || 0) * 100).toFixed(0)}%
                            </Tag>
                        </Tooltip>
                    )}
                </Flex>
            )
        },
        {
            title: '源/类型',
            dataIndex: 'review_type',
            key: 'type',
            width: 100,
            render: (type: string) => (
                <Tag color="default" style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 4, border: '1px solid rgba(255,255,255,0.1)' }}>
                    {type.toUpperCase()}
                </Tag>
            )
        },
        {
            title: '入库时间',
            dataIndex: 'created_at',
            key: 'time',
            width: 160,
            render: (time: string) => <Text type="secondary" style={{ fontSize: 13 }}>{new Date(time).toLocaleString()}</Text>
        },
        {
            title: '操作',
            key: 'action',
            width: 220,
            align: 'center' as const,
            render: (_: unknown, record: DocumentReview) => (
                <Space size="middle">
                    <Button
                        type="primary"
                        ghost
                        size="small"
                        icon={<CheckCircleOutlined />}
                        onClick={() => handleApprove(record.id)}
                        style={{ borderRadius: 6 }}
                    >
                        通过
                    </Button>
                    <Button
                        danger
                        ghost
                        size="small"
                        icon={<CloseCircleOutlined />}
                        onClick={() => handleReject(record.id)}
                        style={{ borderRadius: 6 }}
                    >
                        驳回
                    </Button>
                    <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handlePreview(record.document_id)}
                        style={{ borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)' }}
                    >
                        预览
                    </Button>
                </Space>
            )
        }
    ];

    return (
        <PageContainer title="数据质量审核 (Data Audit)">
            <div style={{ marginBottom: 32 }}>
                <Title level={3} style={{ marginBottom: 8, fontWeight: 600 }}>数据质量审核控制台</Title>
                <Text type="secondary" style={{ fontSize: 14 }}>
                    对自动清洗后质量评分较低的文档进行人工复核，确保知识库的极高纯净度。
                </Text>
            </div>

            <Card
                styles={{ body: { padding: 0 } }}
                style={{
                    borderRadius: 16,
                    overflow: 'hidden',
                    background: token.colorBgContainer,
                    border: '1px solid rgba(255,255,255,0.05)',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.24)'
                }}
            >
                <Table
                    dataSource={reviews}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 8, size: 'small' }}
                    style={{ background: 'transparent' }}
                    className="audit-table"
                    locale={{
                        emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待审核任务" />
                    }}
                />
            </Card>

            <Drawer
                title={
                    <Space>
                        <SafetyCertificateOutlined style={{ color: token.colorInfo }} />
                        <span>文档深度预览</span>
                        <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>ID: {previewDocId}</Text>
                    </Space>
                }
                open={isPreviewOpen}
                onClose={() => setIsPreviewOpen(false)}
                size="large"
                styles={{ body: { padding: 0 } }}
            >
                {previewLoading ? (
                    <div style={{ padding: 48, textAlign: 'center' }}>
                        <Progress percent={99} status="active" showInfo={false} strokeColor={token.colorInfo} />
                        <Text type="secondary" style={{ marginTop: 16, display: 'block' }}>正在提取原文内容...</Text>
                    </div>
                ) : (
                    <div style={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        background: token.colorBgLayout
                    }}>
                        <div style={{
                            flex: 1,
                            padding: '24px',
                            overflowY: 'auto',
                            lineHeight: 1.8,
                            fontSize: 14,
                            color: 'rgba(255,255,255,0.85)',
                            whiteSpace: 'pre-wrap',
                            fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace'
                        }}>
                            {previewContent}
                        </div>
                        <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.05)', background: token.colorBgContainer, textAlign: 'right' }}>
                            <Button onClick={() => setIsPreviewOpen(false)}>关闭预览</Button>
                        </div>
                    </div>
                )}
            </Drawer>
        </PageContainer>
    );
};
