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

import { useMonitor } from '../hooks/useMonitor';
import { AppError } from '../core/AppError';
import { ErrorCode } from '../core/schema/error';

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
    const { track, report } = useMonitor(); // 🛰️ [FE-GOV]: 注入监控
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
        // 1. 权限异常：标记为 auth 层级，记录用户尝试越权的操作
        if (!hasAccess({ anyPermissions: ['knowledge:manage'] })) {
            const authErr = new AppError({
                code: ErrorCode.API_UNAUTHORIZED,
                message: '当前账号没有创建知识库权限',
                layer: 'auth',
                severity: 'medium',
                metadata: { attemptedAction: 'create_kb', kbName: values.name }
            });
            report(authErr); // 自动上报，后续通过 Trace ID 可追溯是谁在“尝试”越权
            message.warning(authErr.message);
            return;
        }

        // 2. 行为追踪：记录开始创建动作及参数
        track('user_action', 'kb_create_start', { name: values.name, description: values.description });

        try {
            await createMutation.mutateAsync(values);
            message.success(t('common.success'));
            setIsCreateModalOpen(false);
            
            // 3. 成功链路记录
            track('user_action', 'kb_create_success', { name: values.name });
        } catch (err: any) {
            // 4. 故障还原：如果 API 失败，将元数据一起打包上报
            const apiErr = new AppError({
                code: ErrorCode.UNKNOWN_ERROR,
                message: t('common.error'),
                layer: 'business',
                severity: 'high',
                metadata: { 
                    values, // 保留填写的参数，方便复盘时看是否是输入触发了后端边缘 Bug
                    originalError: err.message 
                }
            });
            report(apiErr);
            message.error(apiErr.message);
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
                loading={createMutation.isPending}
            />

            <KnowledgeDetail
                kb={selectedKB}
                open={isDetailOpen}
                onClose={() => setIsDetailOpen(false)}
            />
        </PageContainer>
    );
};
