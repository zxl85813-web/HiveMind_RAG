import React, { useState, useEffect } from 'react';
import { App, Button, Space } from 'antd';
import { PlusOutlined, DatabaseOutlined, SyncOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PageContainer, EmptyState, PermissionButton } from '../components/common';
import { KnowledgeList } from '../components/knowledge/KnowledgeList';
import { CreateKBModal } from '../components/knowledge/CreateKBModal';
import { KnowledgeDetail } from '../components/knowledge/KnowledgeDetail';
import type { CreateKnowledgeBaseParams } from '../services/knowledgeApi';
import type { KnowledgeBase } from '../types';
import { useAuthStore } from '../stores/authStore';
import { useKnowledgeBases, useCreateKBMutation } from '../hooks/queries/useKnowledgeQuery';

import { useSearchParams } from 'react-router-dom';

/**
 * 🛰️ [FE-GOV-001]: 知识库管理页面 (Refactored with React Query)
 */
export const KnowledgePage: React.FC = () => {
    const { message } = App.useApp();
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    
    // Server State
    const { data: kbs = [], isLoading, refetch, isRefetching } = useKnowledgeBases();
    const createMutation = useCreateKBMutation();

    // UI State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);
    const hasAccess = useAuthStore((state) => state.hasAccess);

    // Handle deep link via query params
    useEffect(() => {
        const kbId = searchParams.get('kbId');
        if (kbId && kbs.length > 0) {
            const target = kbs.find(k => k.id === kbId);
            if (target) {
                setSelectedKB(target);
                setIsDetailOpen(true);
            }
        }
    }, [searchParams, kbs]);

    const handleCreate = async (values: CreateKnowledgeBaseParams) => {
        if (!hasAccess({ anyPermissions: ['knowledge:manage'] })) {
            message.warning('当前账号没有创建知识库权限');
            return;
        }

        try {
            await createMutation.mutateAsync(values);
            message.success(t('common.success'));
            setIsCreateModalOpen(false);
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
                    <Button 
                        icon={<SyncOutlined spin={isRefetching} />} 
                        onClick={() => refetch()} 
                        disabled={isLoading}
                    />
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
            {kbs.length === 0 && !isLoading ? (
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
                    loading={isLoading}
                    onSelect={handleSelectKB}
                />
            )}

            <CreateKBModal
                open={isCreateModalOpen}
                onCancel={() => setIsCreateModalOpen(false)}
                onSubmit={handleCreate}
                confirmLoading={createMutation.isPending}
            />

            <KnowledgeDetail
                kb={selectedKB}
                open={isDetailOpen}
                onClose={() => setIsDetailOpen(false)}
            />
        </PageContainer>
    );
};
