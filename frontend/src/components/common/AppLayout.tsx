/**
 * AppLayout — AI-First 全局布局 (修正版)。
 */

import React, { useEffect } from 'react';
import { Layout, Menu, Flex, Badge, Tooltip, App } from 'antd';
import {
    AppstoreOutlined,
    DatabaseOutlined,
    ClusterOutlined,
    BulbOutlined,
    SettingOutlined,
    BellOutlined,
    SafetyCertificateOutlined,
    RocketOutlined,
    LockOutlined,
    LineChartOutlined,
    FolderOpenOutlined,
    SisternodeOutlined,
    RobotOutlined,
    DesktopOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useChatStore } from '../../stores/chatStore';
import { ChatPanel } from '../chat/ChatPanel';
import { CreateKBModal } from '../knowledge/CreateKBModal';
import { useCreateKnowledgeBase } from '../../hooks/useDashboardData';
import type { CreateKnowledgeBaseParams } from '../../services/knowledgeApi';
import styles from './AppLayout.module.css';

const { Sider, Content } = Layout;

export const AppLayout: React.FC = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const { message } = App.useApp();

    const {
        viewMode,
        toggleViewMode,
        panelOpen,
        panelWidth,
        updateContext,
        isCreateKBModalOpen,
        setCreateKBModalOpen
    } = useChatStore();

    const isAIMode = viewMode === 'ai';
    const createKBMutation = useCreateKnowledgeBase();

    /** 导航项 */
    const navItems = [
        { key: '/', label: t('nav.dashboard'), icon: <AppstoreOutlined /> },
        { key: '/knowledge', label: t('nav.knowledge'), icon: <DatabaseOutlined /> },
        { key: '/audit', label: t('nav.audit'), icon: <SafetyCertificateOutlined /> },
        { key: '/security', label: t('nav.security'), icon: <LockOutlined /> },
        { key: '/evaluation', label: t('nav.evaluation'), icon: <LineChartOutlined /> },
        { key: '/finetuning', label: t('nav.finetuning'), icon: <FolderOpenOutlined /> },
        { key: '/pipelines', label: t('nav.pipelines'), icon: <SisternodeOutlined /> },
        { key: '/studio', label: t('nav.studio'), icon: <RocketOutlined /> },
        { key: '/agents', label: t('nav.agents'), icon: <ClusterOutlined /> },
        { key: '/batch', label: t('nav.batch'), icon: <ClusterOutlined /> },
        { key: '/learning', label: t('nav.learning'), icon: <BulbOutlined /> },
        { key: '/settings', label: t('nav.settings'), icon: <SettingOutlined /> },
    ];

    const toggleLang = () => {
        const current = i18n.language;
        const next = current.startsWith('zh') ? 'en-US' : 'zh-CN';
        i18n.changeLanguage(next);
    };

    /** 路由变化时更新 Chat 上下文 */
    useEffect(() => {
        updateContext(location.pathname);
    }, [location.pathname, updateContext]);

    /** 当前活跃路由 */
    const activeKey = location.pathname === '/'
        ? '/'
        : '/' + (location.pathname.split('/')[1] || '');

    /** 处理侧边栏导航 */
    const handleNavClick = ({ key }: { key: string }) => {
        if (isAIMode) {
            useChatStore.getState().setViewMode('classic');
        }
        navigate(key);
    };

    /** 全局创建知识库处理 */
    const handleCreateKB = async (values: CreateKnowledgeBaseParams) => {
        try {
            await createKBMutation.mutateAsync(values);
            message.success(t('knowledge.createSuccess') || "知识库申请已提交并就绪");
            setCreateKBModalOpen(false);
            if (location.pathname !== '/knowledge') {
                navigate('/knowledge');
            }
        } catch {
            message.error("创建知识库失败，请检查连接");
        }
    };

    return (
        <Layout className={styles.layout}>
            {!isAIMode && (
                <Sider width={240} className={styles.sider} theme="dark">
                    <Flex vertical className={styles.siderInner}>
                        <div className={styles.logo} onClick={() => {
                            useChatStore.getState().setViewMode('ai');
                            navigate('/');
                        }}>
                            <span className={styles.logoMark}>⬡</span>
                            <span className={styles.logoText}>HiveMind</span>
                        </div>
                        <Menu
                            mode="inline"
                            selectedKeys={[activeKey]}
                            onClick={handleNavClick}
                            items={navItems}
                            className={styles.nav}
                        />
                        <Flex align="center" justify="space-between" className={styles.siderFooter}>
                            <Flex gap={12}>
                                <Tooltip title={t('common.language')} placement="top">
                                    <span className={styles.siderAction} onClick={toggleLang}>
                                        {i18n.language.startsWith('zh') ? 'EN' : '中'}
                                    </span>
                                </Tooltip>
                                <Badge count={0} size="small">
                                    <BellOutlined className={styles.siderAction} />
                                </Badge>
                            </Flex>
                            <Flex align="center" gap={8}>
                                <span className={styles.statusText}>Online</span>
                                <div className={styles.statusDot} />
                            </Flex>
                        </Flex>
                    </Flex>
                </Sider>
            )}

            <Layout className={styles.mainLayout}>
                <div className={styles.modeSwitcher}>
                    <Tooltip title={isAIMode ? '切换到传统模式' : '切换到 AI 模式'} placement="bottomLeft">
                        <button
                            className={`${styles.modeSwitchBtn} ${isAIMode ? styles.modeSwitchAI : styles.modeSwitchClassic}`}
                            onClick={toggleViewMode}
                        >
                            {isAIMode ? (
                                <><DesktopOutlined /><span className={styles.modeSwitchLabel}>传统模式</span></>
                            ) : (
                                <><RobotOutlined /><span className={styles.modeSwitchLabel}>AI 模式</span></>
                            )}
                        </button>
                    </Tooltip>
                </div>

                {isAIMode ? (
                    <Content className={styles.aiModeContent}>
                        <div className={styles.aiModeChatWrap}>
                            <ChatPanel />
                        </div>
                    </Content>
                ) : (
                    <>
                        <Content className={styles.content}>
                            <div className={styles.contentInner}>
                                <Outlet />
                            </div>
                        </Content>
                        <div className={styles.chatPanelWrap} style={{ width: panelOpen ? panelWidth : 48 }}>
                            <ChatPanel />
                        </div>
                    </>
                )}
            </Layout>

            <CreateKBModal
                open={isCreateKBModalOpen}
                onCancel={() => setCreateKBModalOpen(false)}
                onSubmit={handleCreateKB}
            />
        </Layout>
    );
};
