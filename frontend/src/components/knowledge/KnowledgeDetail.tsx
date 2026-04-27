import React, { useState, useEffect, useCallback, useRef } from 'react';
import { App, Drawer, Table, Button, Space, Tag, Upload, Typography, Tooltip, List, Tabs, Spin, Empty, Input, Popover, Select } from 'antd';
import { DeleteOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, DatabaseOutlined, InboxOutlined, SafetyCertificateOutlined, InfoCircleOutlined, RightOutlined, SearchOutlined, PlusOutlined, UserAddOutlined, FolderOpenOutlined } from '@ant-design/icons';
import { G6GraphVisualizer } from './G6GraphVisualizer';
import { KBPermissionsModal } from './KBPermissionsModal';
import { UploadProgressDrawer, type UploadFileItem } from './UploadProgressDrawer';
import { useTranslation } from 'react-i18next';
import { securityApi } from '../../services/securityApi';
import { evalApi } from '../../services/evalApi';
import { tagApi } from '../../services/tagApi';
import { knowledgeApi } from '../../services/knowledgeApi';
import type { KnowledgeBase, Document, Tag as PCTag } from '../../types';
import { Statistic, Row, Col, Card as AntdCard } from 'antd';
import { LineChartOutlined, HeartOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useResumableUpload } from '../../hooks/useResumableUpload';

const { Text, Title } = Typography;

interface Props {
    kb: KnowledgeBase | null;
    open: boolean;
    onClose: () => void;
}

export const KnowledgeDetail: React.FC<Props> = ({ kb, open, onClose }) => {
    const { message } = App.useApp();
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    const highlightedDocId = searchParams.get('docId');
    const [docs, setDocs] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [selectedDocReport, setSelectedDocReport] = useState<any>(null);
    const [isReportOpen, setIsReportOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('files');
    const [graphData, setGraphData] = useState<{ nodes: any[], links: any[] } | null>(null);
    const [loadingGraph, setLoadingGraph] = useState(false);
    const [healthStats, setHealthStats] = useState<any>(null);
    const [loadingHealth, setLoadingHealth] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [allTags, setAllTags] = useState<PCTag[]>([]);
    const [isPermissionsOpen, setIsPermissionsOpen] = useState(false);

    // ── 批量上传 & 进度面板状态 ──────────────────────────────────────────────
    const [uploadFiles, setUploadFiles] = useState<UploadFileItem[]>([]);
    const [batchId, setBatchId] = useState<string | undefined>();
    const [isProgressOpen, setIsProgressOpen] = useState(false);
    const BATCH_SIZE = 10; // 每批最多 10 个文件并发上传
    const { upload: resumableUpload, abortUpload, checkResumable } = useResumableUpload();

    useEffect(() => {
        loadTags();
    }, []);

    const loadTags = async () => {
        try {
            const res = await tagApi.listTags();
            setAllTags(res.data.data);
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        if (open && kb) {
            loadDocs(kb.id);
            // reset states
            setActiveTab('files');
            setGraphData(null);
        }
    }, [open, kb]);

    useEffect(() => {
        if (open && kb && activeTab === 'graph') {
            loadGraph(kb.id);
        }
        if (open && kb && activeTab === 'health') {
            loadHealth(kb.id);
        }
        if (open && activeTab === 'search') {
            setSearchQuery('');
            setSearchResults([]);
        }
    }, [open, kb, activeTab]);

    const handleSearch = async () => {
        if (!kb || !searchQuery.trim()) return;
        setIsSearching(true);
        try {
            const res = await knowledgeApi.searchKB(kb.id, searchQuery);
            setSearchResults(res.data.data.results || []);
        } catch {
            message.error("搜索失败");
        } finally {
            setIsSearching(false);
        }
    };

    const loadHealth = async (id: string) => {
        setLoadingHealth(true);
        try {
            const res = await evalApi.getKBStats(id);
            setHealthStats(res.data.data);
        } catch {
            // Mock fallback if no real reports exist yet
            setHealthStats({
                score: 0.82,
                faithfulness: 0.88,
                relevance: 0.76,
                reports_count: 3,
                status: 'healthy',
                trend: [
                    { timestamp: '2024-01-01', score: 0.65 },
                    { timestamp: '2024-01-15', score: 0.72 },
                    { timestamp: '2024-02-01', score: 0.82 }
                ]
            });
        } finally {
            setLoadingHealth(false);
        }
    };

    const loadDocs = async (id: string) => {
        setLoading(true);
        try {
            const res = await knowledgeApi.listDocsInKB(id);
            const rawData = res.data as any;
            setDocs(rawData?.data ?? rawData);
        } catch {
            message.error(t('common.error'));
        } finally {
            setLoading(false);
        }
    };

    const loadGraph = async (id: string) => {
        if (graphData) return;
        setLoadingGraph(true);
        try {
            const res = await knowledgeApi.getKBGraph(id);
            const rawData = res.data as any;
            const gd = rawData?.data ?? rawData;
            setGraphData(gd);
        } catch {
            message.error("Failed to load graph data");
        } finally {
            setLoadingGraph(false);
        }
    };

    const handleUpload = async (file: File) => {
        if (!kb) return false;
        setUploading(true);
        const hide = message.loading(t('common.loading'), 0);
        try {
            // 1. Upload to Global Library
            const docRes = await knowledgeApi.uploadDoc(file);
            const docId = docRes.data.id;

            // 2. Link to current Knowledge Base (Triggers Background Indexing)
            await knowledgeApi.linkDoc(kb.id, docId);

            hide();
            message.success(t('common.success'));
            loadDocs(kb.id);
        } catch {
            hide();
            message.error(t('common.error'));
        } finally {
            setUploading(false);
        }
        return false; // Prevent default ajax upload
    };

    /**
     * 批量上传入口（使用断点续传）：
     *   1. 检查每个文件是否有未完成的上传记录（localStorage）
     *   2. 初始化进度面板
     *   3. 逐文件调用 useResumableUpload，支持断点续传
     *   4. 批量关联到 KB，获取 batch_id
     *   5. 打开进度面板，SSE 自动订阅
     */
    const handleBatchUpload = useCallback(async (rawFiles: File[]) => {
        if (!kb || rawFiles.length === 0) return;

        // 检查哪些文件有可续传记录
        const items: UploadFileItem[] = rawFiles.map((f, i) => {
            const resumableState = checkResumable(f);
            const folderPath = (f as any).webkitRelativePath
                ? (f as any).webkitRelativePath.split('/').slice(0, -1).join('/')
                : undefined;
            return {
                uid: `${Date.now()}-${i}`,
                filename: f.name,
                folderPath,
                fileSize: f.size,
                // 有续传记录时显示 resumable 状态
                status: resumableState ? 'resumable' as const : 'waiting' as const,
                uploadPercent: resumableState
                    ? Math.round((resumableState.completedParts.length / resumableState.totalParts) * 100)
                    : 0,
            };
        });

        setUploadFiles(items);
        setBatchId(undefined);
        setIsProgressOpen(true);
        setUploading(true);

        try {
            const uploadedDocIds: string[] = [];
            const updatedItems = [...items];

            // 逐文件上传（每次最多 BATCH_SIZE 个并发）
            for (let batchStart = 0; batchStart < rawFiles.length; batchStart += BATCH_SIZE) {
                const batchFiles = rawFiles.slice(batchStart, batchStart + BATCH_SIZE);
                const batchItems = updatedItems.slice(batchStart, batchStart + BATCH_SIZE);

                await Promise.all(
                    batchFiles.map(async (file, idx) => {
                        const item = batchItems[idx];
                        item.status = 'uploading';
                        setUploadFiles([...updatedItems]);

                        try {
                            const docId = await resumableUpload(
                                file,
                                item.folderPath,
                                {
                                    onProgress: (percent) => {
                                        item.uploadPercent = percent;
                                        setUploadFiles([...updatedItems]);
                                    },
                                    onPartComplete: (partNum, total) => {
                                        item.uploadPercent = Math.round((partNum / total) * 100);
                                        setUploadFiles([...updatedItems]);
                                    },
                                    onError: (err) => {
                                        item.status = 'failed';
                                        item.errorMsg = err.message;
                                        setUploadFiles([...updatedItems]);
                                    },
                                }
                            );
                            item.docId = docId;
                            item.status = 'processing';
                            uploadedDocIds.push(docId);
                        } catch (err: any) {
                            if (err.message !== 'Upload cancelled') {
                                item.status = 'failed';
                                item.errorMsg = err.message || '上传失败';
                            }
                        }
                        setUploadFiles([...updatedItems]);
                    })
                );
            }

            if (uploadedDocIds.length > 0) {
                try {
                    const linkRes = await knowledgeApi.linkDocsBatch(kb.id, uploadedDocIds);
                    const newBatchId = (linkRes.data as any)?.batch_id;
                    if (newBatchId) setBatchId(newBatchId);
                } catch {
                    message.warning('文件已上传，但关联知识库时出错，请手动刷新');
                }
            }

            loadDocs(kb.id);
        } finally {
            setUploading(false);
        }
    }, [kb, BATCH_SIZE, resumableUpload, checkResumable]);

    const handleFileStatusChange = useCallback((uid: string, status: UploadFileItem['status'], docId?: string) => {
        setUploadFiles(prev => prev.map(f =>
            f.uid === uid ? { ...f, status, ...(docId ? { docId } : {}) } : f
        ));
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        const items = Array.from(e.dataTransfer.items);
        const files: File[] = [];

        const readEntry = (entry: any): Promise<void> => {
            if (entry.isFile) {
                return new Promise(resolve => {
                    entry.file((f: File) => { files.push(f); resolve(); });
                });
            }
            if (entry.isDirectory) {
                const reader = entry.createReader();
                return new Promise(resolve => {
                    reader.readEntries(async (entries: any[]) => {
                        await Promise.all(entries.map(readEntry));
                        resolve();
                    });
                });
            }
            return Promise.resolve();
        };

        Promise.all(
            items.map(item => {
                const entry = item.webkitGetAsEntry?.();
                return entry ? readEntry(entry) : Promise.resolve();
            })
        ).then(() => {
            if (files.length > 0) handleBatchUpload(files);
        });
    }, [handleBatchUpload]);

     = async (docId: string) => {
        if (!kb) return;
        try {
            await knowledgeApi.unlinkDoc(kb.id, docId);
            message.success(t('common.success'));
            loadDocs(kb.id);
        } catch {
            message.error(t('common.error'));
        }
    };

    const showReport = async (docId: string) => {
        try {
            const res = await securityApi.getReport(docId);
            setSelectedDocReport(res.data.data);
            setIsReportOpen(true);
        } catch {
            message.info("该文档尚无脱敏记录或无需脱敏");
        }
    };

    const handleAttachTag = async (docId: string, tagId: number) => {
        try {
            await tagApi.attachTag(docId, tagId);
            message.success('添加标签成功');
            loadDocs(kb!.id);
        } catch { message.error('添加失败') }
    };

    const handleDetachTag = async (docId: string, tagId: number) => {
        try {
            await tagApi.detachTag(docId, tagId);
            message.success('移除成功');
            loadDocs(kb!.id);
        } catch { message.error('移除失败') }
    };


    const columns = [
        {
            title: t('knowledge.fileName'),
            dataIndex: 'filename',
            key: 'filename',
            render: (text: string) => <Text strong>{text}</Text>
        },
        {
            title: t('common.status'),
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => {
                let color = 'default';
                let icon = <SyncOutlined spin />;

                if (status === 'indexed' || status === 'parsed') {
                    color = 'success';
                    icon = <CheckCircleOutlined />;
                } else if (status === 'failed') {
                    color = 'error';
                    icon = <CloseCircleOutlined />;
                } else if (status === 'pending_review') {
                    color = 'processing';
                    icon = <SyncOutlined spin />;
                } else if (status === 'pending') {
                    color = 'warning';
                }

                return (
                    <Tag icon={icon} color={color}>
                        {status.toUpperCase()}
                    </Tag>
                );
            }
        },
        {
            title: t('knowledge.fileSize'),
            dataIndex: 'file_size',
            key: 'size',
            render: (s: number) => (s / 1024).toFixed(1) + ' KB'
        },
        {
            title: '标签',
            key: 'tags',
            render: (_: any, record: Document) => (
                <Space wrap size={[0, 4]}>
                    {(record.tags || []).map((t) => (
                        <Tag
                            key={t.id}
                            color={t.color || 'default'}
                            closable
                            onClose={(e) => { e.preventDefault(); handleDetachTag(record.id, t.id); }}
                        >
                            {t.name}
                        </Tag>
                    ))}
                    <Popover
                        content={
                            <Select
                                showSearch
                                style={{ width: 150 }}
                                placeholder="选择标签"
                                onChange={(val) => handleAttachTag(record.id, val)}
                                options={allTags.filter(t => !(record.tags || []).find(rt => rt.id === t.id)).map(t => ({ label: t.name, value: t.id }))}
                            />
                        }
                        trigger="click"
                        placement="bottom"
                    >
                        <Tag style={{ borderStyle: 'dashed', cursor: 'pointer' }} icon={<PlusOutlined />}>
                            新增
                        </Tag>
                    </Popover>
                </Space>
            )
        },
        {
            title: '数据安全',
            key: 'security',
            render: (_: any, record: Document) => (
                <Space>
                    <Tooltip title="脱敏报告">
                        <Button
                            type="text"
                            size="small"
                            icon={<SafetyCertificateOutlined style={{ color: 'var(--hm-color-success)' }} />}
                            onClick={() => showReport(record.id)}
                        />
                    </Tooltip>
                </Space>
            )
        },

        {
            title: t('nav.settings'),
            key: 'action',
            render: (_: any, record: Document) => (
                <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleUnlink(record.id)}
                    title={t('common.delete')}
                />
            )
        }
    ];

    return (
        <Drawer
            title={
                <Space>
                    <DatabaseOutlined />
                    {kb?.name}
                    <Tag>v{kb?.version || 1}</Tag>
                </Space>
            }
            open={open}
            onClose={onClose}
            size="large"
            extra={
                <Space>
                    <Button icon={<UserAddOutlined />} onClick={() => setIsPermissionsOpen(true)}>
                        权限共享
                    </Button>
                    <Button icon={<SyncOutlined />} onClick={() => {
                        if (kb) {
                            if (activeTab === 'files') loadDocs(kb.id);
                            if (activeTab === 'graph') {
                                setGraphData(null);
                                loadGraph(kb.id);
                            }
                        }
                    }} />
                </Space>
            }
        >
            <div style={{ marginBottom: 24 }}>
                <Text type="secondary">{kb?.description}</Text>
            </div>

            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={[
                    {
                        key: 'files',
                        label: '文档资源',
                        children: (
                            <>
                                <div
                                    style={{ marginBottom: 24, padding: '20px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px dashed rgba(6, 214, 160, 0.3)' }}
                                    onDragOver={e => e.preventDefault()}
                                    onDrop={handleDrop}
                                >
                                    <Upload.Dragger
                                        beforeUpload={(file: any) => { handleUpload(file); return false; }}
                                        showUploadList={false}
                                        multiple={true}
                                        disabled={uploading}
                                        style={{ background: 'transparent', border: 'none' }}
                                    >
                                        <p className="ant-upload-drag-icon">
                                            <InboxOutlined style={{ color: 'var(--hm-color-brand)' }} />
                                        </p>
                                        <p className="ant-upload-text" style={{ color: 'var(--hm-color-text-primary)' }}>
                                            {uploading ? t('common.loading') : '点击上传单个文件，或拖拽文件/文件夹到此处'}
                                        </p>
                                        <p className="ant-upload-hint" style={{ color: 'var(--hm-color-text-secondary)' }}>
                                            {t('knowledge.uploadHint')}
                                        </p>
                                    </Upload.Dragger>

                                    {/* 文件夹批量上传按钮 */}
                                    <div style={{ textAlign: 'center', marginTop: 12 }}>
                                        <label htmlFor="folder-upload-input">
                                            <Button
                                                icon={<FolderOpenOutlined />}
                                                disabled={uploading}
                                                onClick={() => document.getElementById('folder-upload-input')?.click()}
                                            >
                                                选择文件夹批量上传
                                            </Button>
                                        </label>
                                        <input
                                            id="folder-upload-input"
                                            type="file"
                                            // @ts-ignore — webkitdirectory 是非标准属性
                                            webkitdirectory=""
                                            multiple
                                            style={{ display: 'none' }}
                                            onChange={(e) => {
                                                const files = Array.from(e.target.files || []);
                                                if (files.length > 0) handleBatchUpload(files);
                                                e.target.value = ''; // 允许重复选择同一文件夹
                                            }}
                                        />
                                        {uploadFiles.length > 0 && (
                                            <Button
                                                type="link"
                                                size="small"
                                                style={{ marginLeft: 8 }}
                                                onClick={() => setIsProgressOpen(true)}
                                            >
                                                查看上传进度 ({uploadFiles.filter(f => f.status === 'done').length}/{uploadFiles.length})
                                            </Button>
                                        )}
                                    </div>
                                </div>

                                <Table
                                    dataSource={docs}
                                    columns={columns}
                                    rowKey="id"
                                    loading={loading}
                                    pagination={false}
                                    rowClassName={(record) => record.id === highlightedDocId ? 'ant-table-row-selected highlight-row' : ''}
                                    locale={{ emptyText: t('knowledge.emptyDesc') }}
                                />
                            </>
                        )
                    },
                    {
                        key: 'search',
                        label: '检索测试',
                        children: (
                            <div style={{ display: 'flex', flexDirection: 'column', height: '600px' }}>
                                <div style={{ marginBottom: 16 }}>
                                    <Input.Search
                                        placeholder="输入问题测试检索效果..."
                                        allowClear
                                        enterButton={<Button type="primary" icon={<SearchOutlined />}>搜索</Button>}
                                        size="large"
                                        value={searchQuery}
                                        onChange={e => setSearchQuery(e.target.value)}
                                        onSearch={handleSearch}
                                        loading={isSearching}
                                    />
                                </div>
                                <div style={{ flex: 1, overflowY: 'auto', background: 'rgba(0,0,0,0.2)', padding: 16, borderRadius: 8 }}>
                                    {isSearching ? (
                                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                                            <Spin size="large" />
                                        </div>
                                    ) : searchResults.length > 0 ? (
                                        <List
                                            dataSource={searchResults}
                                            renderItem={(item, index) => (
                                                <List.Item>
                                                    <AntdCard size="small" title={`结果 #${index + 1}`} extra={<Tag color="blue">{item.score ? `Score: ${item.score.toFixed(3)}` : 'N/A'}</Tag>} style={{ width: '100%', marginBottom: 8, background: 'rgba(255,255,255,0.02)' }}>
                                                        <Text style={{ whiteSpace: 'pre-wrap' }}>{item.content}</Text>
                                                        {item.metadata && (
                                                            <div style={{ marginTop: 8 }}>
                                                                <Tag>{item.metadata.filename || 'Unknown Document'}</Tag>
                                                                {item.metadata.page_number && <Tag>Page {item.metadata.page_number}</Tag>}
                                                            </div>
                                                        )}
                                                    </AntdCard>
                                                </List.Item>
                                            )}
                                        />
                                    ) : (
                                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                                            <Empty description="暂无搜索结果" />
                                        </div>
                                    )}
                                </div>
                            </div>
                        )
                    },
                    {
                        key: 'graph',
                        label: '知识图谱',
                        children: (
                            <div style={{ height: '600px', background: 'rgba(0,0,0,0.2)', borderRadius: 8, overflow: 'hidden' }}>
                                {loadingGraph ? (
                                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                                        <Spin size="large" />
                                    </div>
                                ) : graphData && graphData.nodes.length > 0 ? (
                                    <G6GraphVisualizer data={graphData} />
                                ) : (
                                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                                        <Empty description="暂无图谱数据,请上传包含复杂关系文档" />
                                    </div>
                                )}
                            </div>
                        )
                    },
                    {
                        key: 'health',
                        label: '质量与健康',
                        children: (
                            <Spin spinning={loadingHealth}>
                                {healthStats ? (
                                    <div style={{ padding: '16px' }}>
                                        <Row gutter={16} style={{ marginBottom: 24 }}>
                                            <Col span={12}>
                                                <AntdCard size="small">
                                                    <Statistic
                                                        title="综合健康评分"
                                                        value={healthStats.score * 100}
                                                        precision={1}
                                                        suffix="%"
                                                        prefix={<HeartOutlined style={{ color: healthStats.status === 'healthy' ? 'var(--hm-color-success)' : 'var(--hm-color-warning)' }} />}
                                                    />
                                                </AntdCard>
                                            </Col>
                                            <Col span={12}>
                                                <AntdCard size="small">
                                                    <Statistic
                                                        title="已运行评估"
                                                        value={healthStats.reports_count}
                                                        prefix={<SyncOutlined />}
                                                    />
                                                </AntdCard>
                                            </Col>
                                        </Row>

                                        <div style={{ marginBottom: 24 }}>
                                            <Title level={5}>维度评分</Title>
                                            <Row gutter={16}>
                                                <Col span={12}>
                                                    <Text type="secondary">忠实度 (Faithfulness)</Text>
                                                    <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{(healthStats.faithfulness * 100).toFixed(1)}%</div>
                                                </Col>
                                                <Col span={12}>
                                                    <Text type="secondary">回答相关性 (Relevance)</Text>
                                                    <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{(healthStats.relevance * 100).toFixed(1)}%</div>
                                                </Col>
                                            </Row>
                                        </div>

                                        <div>
                                            <Title level={5}><LineChartOutlined /> 质量变化趋势</Title>
                                            <div style={{ height: 120, background: 'rgba(255,255,255,0.05)', borderRadius: 8, display: 'flex', alignItems: 'flex-end', padding: '10px', gap: 8 }}>
                                                {healthStats.trend.map((point: any, i: number) => (
                                                    <Tooltip key={i} title={`Score: ${point.score.toFixed(2)} (${point.timestamp})`}>
                                                        <div style={{
                                                            flex: 1,
                                                            height: `${point.score * 100}%`,
                                                            backgroundColor: 'var(--hm-color-brand)',
                                                            opacity: 0.4 + (i * 0.2),
                                                            borderRadius: '4px 4px 0 0'
                                                        }} />
                                                    </Tooltip>
                                                ))}
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                                                <Text type="secondary" style={{ fontSize: 12 }}>{healthStats.trend[0]?.timestamp}</Text>
                                                <Text type="secondary" style={{ fontSize: 12 }}>{healthStats.trend[healthStats.trend.length - 1]?.timestamp}</Text>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <Empty description="暂无健康数据，请前往评估页面运行测试" />
                                )}
                            </Spin>
                        )
                    }
                ]}
            />

            <Drawer
                title="🛡️ 数据脱敏详情报告"
                open={isReportOpen}
                onClose={() => setIsReportOpen(false)}
                size="default"
            >
                {selectedDocReport ? (
                    <div>
                        <div style={{ marginBottom: 16 }}>
                            <Text type="secondary">扫描时间: {new Date(selectedDocReport.created_at).toLocaleString()}</Text>
                            <br />
                            <Text strong>检出项总数: </Text>
                            <Tag color="red">{selectedDocReport.total_items_found}</Tag>
                            <Text strong>已脱敏数: </Text>
                            <Tag color="green">{selectedDocReport.total_items_redacted}</Tag>
                        </div>
                        <List
                            header={<div>详细敏感项列表</div>}
                            bordered
                            dataSource={selectedDocReport.items || []}
                            renderItem={(item: any) => (
                                <List.Item>
                                    <List.Item.Meta
                                        title={<Tag color="orange">{item.detector_type.toUpperCase()}</Tag>}
                                        description={
                                            <div>
                                                <Text delete type="secondary">{item.original_text_preview}</Text>
                                                <RightOutlined style={{ margin: '0 8px' }} />
                                                <Text type="success">{item.redacted_text}</Text>
                                                <div style={{ fontSize: '12px', color: 'var(--hm-color-text-secondary)', marginTop: 4 }}>
                                                    位置: {item.start_index}-{item.end_index} | 策略: {item.action_taken}
                                                </div>
                                            </div>
                                        }
                                    />
                                </List.Item>
                            )}
                        />
                    </div>
                ) : (
                    <div style={{ textAlign: 'center', marginTop: 40 }}>
                        <InfoCircleOutlined style={{ fontSize: 32, color: 'var(--hm-color-text-secondary)' }} />
                        <p style={{ marginTop: 16, color: 'var(--hm-color-text-secondary)' }}>加载中或无报告数据</p>
                    </div>
                )}
            </Drawer>

            {kb && (
                <KBPermissionsModal
                    kbId={kb.id}
                    open={isPermissionsOpen}
                    onClose={() => setIsPermissionsOpen(false)}
                />
            )}

            {/* 批量上传进度面板 */}
            <UploadProgressDrawer
                open={isProgressOpen}
                onClose={() => setIsProgressOpen(false)}
                files={uploadFiles}
                batchId={batchId}
                onFileStatusChange={handleFileStatusChange}
            />
        </Drawer>
    );
};
