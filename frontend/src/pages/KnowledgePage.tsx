import React, { useState, useEffect } from 'react';
import { App, Button, Space } from 'antd';
import { PlusOutlined, DatabaseOutlined, SyncOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer, EmptyState, PermissionButton } from '../components/common';
import { KnowledgeList } from '../components/knowledge/KnowledgeList';
import { CreateKBModal } from '../components/knowledge/CreateKBModal';
import { KnowledgeDetail } from '../components/knowledge/KnowledgeDetail';
import { knowledgeApi } from '../services/knowledgeApi';
import type { CreateKnowledgeBaseParams } from '../services/knowledgeApi';
import type { KnowledgeBase } from '../types';
import { useAuthStore } from '../stores/authStore';

import { useSearchParams } from 'react-router-dom';

export const KnowledgePage: React.FC = () => {
    const { message } = App.useApp();
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [loading, setLoading] = useState(false);

    // UI State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);
    const hasAccess = useAuthStore((state) => state.hasAccess);

    const loadData = async () => {
        setLoading(true);
        try {
            const res = await knowledgeApi.listKBs();
            const data = res.data.data;
            setKbs(data);

            // Handle deep link via query params
            const kbId = searchParams.get('kbId');
            if (kbId) {
                const target = data.find(k => k.id === kbId);
                if (target) {
                    setSelectedKB(target);
                    setIsDetailOpen(true);
                }
            }
        } catch {
            message.error(t('common.error'));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, [searchParams]);

    const handleCreate = async (values: CreateKnowledgeBaseParams) => {
        if (!hasAccess({ anyPermissions: ['knowledge:manage'] })) {
            message.warning('当前账号没有创建知识库权限');
            return;
        }

        try {
            await knowledgeApi.createKB(values);
            message.success(t('common.success'));
            setIsCreateModalOpen(false);
            loadData();
        } catch {
            message.error(t('common.error'));
        }
    };

    const handleSelectKB = (kb: KnowledgeBase) => {
        setSelectedKB(kb);
        setIsDetailOpen(true);
    };

    return (
        <PageContainer
            title={t('knowledge.title')}
            description={t('nav.knowledge')}
            actions={
                <Space>
                    <Button icon={<SyncOutlined />} onClick={loadData} />
                    <PermissionButton
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setIsCreateModalOpen(true)}
                        access={{ anyPermissions: ['knowledge:manage'] }}
                    >
                        {t('common.create')}
                    </PermissionButton>
                </Space>
            }
        >
            {kbs.length === 0 && !loading ? (
                <EmptyState
                    icon={<DatabaseOutlined />}
                    title={t('knowledge.emptyTitle')}
                    description={t('knowledge.emptyDesc')}
                    action={
                        <PermissionButton
                            type="primary"
                            onClick={() => setIsCreateModalOpen(true)}
                            access={{ anyPermissions: ['knowledge:manage'] }}
                        >
                            {t('common.create')}
                        </PermissionButton>
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
