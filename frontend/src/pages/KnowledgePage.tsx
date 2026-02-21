import React, { useState, useEffect } from 'react';
import { Button, message, Space } from 'antd';
import { PlusOutlined, DatabaseOutlined, SyncOutlined } from '@ant-design/icons';
import { PageContainer, EmptyState } from '../components/common';
import { KnowledgeList } from '../components/knowledge/KnowledgeList';
import { CreateKBModal } from '../components/knowledge/CreateKBModal';
import { KnowledgeDetail } from '../components/knowledge/KnowledgeDetail';
import { knowledgeApi } from '../services/knowledgeApi';
import type { CreateKnowledgeBaseParams } from '../services/knowledgeApi';
import type { KnowledgeBase } from '../types';

export const KnowledgePage: React.FC = () => {
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [loading, setLoading] = useState(false);

    // UI State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);

    const loadData = async () => {
        setLoading(true);
        try {
            const res = await knowledgeApi.listKBs();
            setKbs(res.data.data);
        } catch (error) {
            message.error("加载知识库列表失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleCreate = async (values: CreateKnowledgeBaseParams) => {
        try {
            await knowledgeApi.createKB(values);
            message.success("知识库创建成功");
            setIsCreateModalOpen(false);
            loadData();
        } catch (e) {
            message.error("创建失败");
        }
    };

    const handleSelectKB = (kb: KnowledgeBase) => {
        setSelectedKB(kb);
        setIsDetailOpen(true);
    };

    return (
        <PageContainer
            title="知识库管理"
            description="管理文档知识库，上传文档并构建向量索引"
            actions={
                <Space>
                    <Button icon={<SyncOutlined />} onClick={loadData} title="刷新列表" />
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
                        创建知识库
                    </Button>
                </Space>
            }
        >
            {kbs.length === 0 && !loading ? (
                <EmptyState
                    icon={<DatabaseOutlined />}
                    title="还没有知识库"
                    description="点击右上角「创建知识库」开始"
                    action={
                        <Button type="primary" onClick={() => setIsCreateModalOpen(true)}>
                            立即创建
                        </Button>
                    }
                />
            ) : (
                <KnowledgeList
                    kbs={kbs}
                    loading={loading}
                    onSelect={handleSelectKB}
                />
            )}

            <CreateKBModal
                open={isCreateModalOpen}
                onCancel={() => setIsCreateModalOpen(false)}
                onSubmit={handleCreate}
            />

            <KnowledgeDetail
                kb={selectedKB}
                open={isDetailOpen}
                onClose={() => setIsDetailOpen(false)}
            />
        </PageContainer>
    );
};
