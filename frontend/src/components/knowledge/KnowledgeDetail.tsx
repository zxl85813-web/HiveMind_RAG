import React, { useState, useEffect } from 'react';
import { Drawer, Table, Button, Space, Tag, Upload, message, Typography } from 'antd';
import { DeleteOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, DatabaseOutlined, InboxOutlined } from '@ant-design/icons';
import type { KnowledgeBase, Document } from '../../types';
import { knowledgeApi } from '../../services/knowledgeApi';

const { Text } = Typography;

interface Props {
    kb: KnowledgeBase | null;
    open: boolean;
    onClose: () => void;
}

export const KnowledgeDetail: React.FC<Props> = ({ kb, open, onClose }) => {
    const [docs, setDocs] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);

    useEffect(() => {
        if (open && kb) {
            loadDocs(kb.id);
        }
    }, [open, kb]);

    const loadDocs = async (id: string) => {
        setLoading(true);
        try {
            const res = await knowledgeApi.listDocsInKB(id);
            setDocs(res.data);
        } catch (e) {
            message.error("加载文档列表失败");
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async (file: File) => {
        if (!kb) return false;
        setUploading(true);
        const hide = message.loading('正在上传并处理...', 0);
        try {
            // 1. Upload to Global Library
            const docRes = await knowledgeApi.uploadDoc(file);
            const docId = docRes.data.id;

            // 2. Link to current Knowledge Base (Triggers Background Indexing)
            await knowledgeApi.linkDoc(kb.id, docId);

            hide();
            message.success("文档已添加，正在后台索引");
            loadDocs(kb.id);
        } catch (e) {
            hide();
            message.error("上传处理失败");
        } finally {
            setUploading(false);
        }
        return false; // Prevent default ajax upload
    };

    const handleUnlink = async (docId: string) => {
        if (!kb) return;
        try {
            await knowledgeApi.unlinkDoc(kb.id, docId);
            message.success("文档已从当前知识库移除 (保留在全局库)");
            loadDocs(kb.id);
        } catch (e) {
            message.error("移除失败");
        }
    };

    const columns = [
        {
            title: '文件名',
            dataIndex: 'filename',
            key: 'filename',
            render: (text: string) => <Text strong>{text}</Text>
        },
        {
            title: '状态',
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
            title: '大小',
            dataIndex: 'file_size',
            key: 'size',
            render: (s: number) => (s / 1024).toFixed(1) + ' KB'
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: Document) => (
                <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleUnlink(record.id)}
                    title="移除关联"
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
            width={800}
            extra={
                <Space>
                    <Button icon={<SyncOutlined />} onClick={() => kb && loadDocs(kb.id)} />
                </Space>
            }
        >
            <div style={{ marginBottom: 24 }}>
                <Text type="secondary">{kb?.description}</Text>
            </div>

            <div style={{ marginBottom: 24, padding: '20px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px dashed rgba(6, 214, 160, 0.3)' }}>
                <Upload.Dragger
                    beforeUpload={handleUpload as any}
                    showUploadList={false}
                    multiple={false}
                    disabled={uploading}
                    style={{ background: 'transparent', border: 'none' }}
                >
                    <p className="ant-upload-drag-icon">
                        <InboxOutlined style={{ color: 'var(--hm-color-brand)' }} />
                    </p>
                    <p className="ant-upload-text" style={{ color: 'var(--hm-color-text-primary)' }}>
                        {uploading ? '上传并处理中...' : '点击或拖拽文件到此区域上传'}
                    </p>
                    <p className="ant-upload-hint" style={{ color: 'var(--hm-color-text-secondary)' }}>
                        支持 TXT, MD, PDF, DOCX 等格式。将在后台自动完成向量化索引。
                    </p>
                </Upload.Dragger>
            </div>

            <Table
                dataSource={docs}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={false}
                locale={{ emptyText: '暂无文档，请点击右上角上传' }}
            />
        </Drawer>
    );
};
