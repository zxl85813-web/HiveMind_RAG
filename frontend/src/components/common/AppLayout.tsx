/**
 * AppLayout — AI-First 全局布局。
 *
 * 双模式设计:
 *   🤖 AI 模式 (默认): Chat 居中占满，侧边栏自动收缩为图标
 *   📊 传统模式: 侧边栏展开，页面内容在中间，Chat 在右侧面板
 *
 * 右上角提供模式切换按钮。
 *
 * @module components/common
 * @see docs/design/ai-first-frontend.md
 */

import React, { useEffect } from 'react';
import { Layout, Menu, Flex, Badge, Tooltip } from 'antd';
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
import { knowledgeApi } from '../../services/knowledgeApi';
import type { CreateKnowledgeBaseParams } from '../../services/knowledgeApi';
import styles from './AppLayout.module.css';

const { Sider, Content } = Layout;

export const AppLayout: React.FC = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
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

    /** 处理侧边栏导航: 点击则切到传统模式并导航 */
    const handleNavClick = ({ key }: { key: string }) => {
        if (isAIMode) {
            // 从 AI 模式切走 → 自动进入传统模式
            useChatStore.getState().setViewMode('classic');
        }
        navigate(key);
    };

    /** 全局创建知识库处理 */
    const handleCreateKB = async (values: CreateKnowledgeBaseParams) => {
        try {
            await knowledgeApi.createKB(values);
            // 这里使用了 AntApp.useApp() 中的 message，但在 App.tsx 中已经包裹了 AntApp
            // 我们需要确保 AppLayout 能获取到 message
            // 简单起见，这里先用 console.log，或者确保 AppLayout 在 AntApp 下
            console.log("KB Created successfully");
            setCreateKBModalOpen(false);
            // 如果在知识库页面，可能需要通知它刷新，或者干脆跳转过去
            if (location.pathname !== '/knowledge') {
                navigate('/knowledge?refresh=1');
            }
        } catch (e) {
            console.error("Failed to create KB", e);
        }
    };

    return (
        <Layout className={styles.layout}>
            {/* === 左侧全局导航 Sider (仅在传统模式显示) === */}
            {!isAIMode && (
                <Sider
                    width={240}
                    className={styles.sider}
                    theme="dark"
                >
                    <Flex vertical className={styles.siderInner}>
                        {/* Top: Logo */}
                        <div className={styles.logo} onClick={() => {
                            useChatStore.getState().setViewMode('ai');
                            navigate('/');
                        }}>
                            <span className={styles.logoMark}>⬡</span>
                            <span className={styles.logoText}>HiveMind</span>
                        </div>

                        {/* Middle: Nav Menu */}
                        <Menu
                            mode="inline"
                            selectedKeys={[activeKey]}
                            onClick={handleNavClick}
                            items={navItems}
                            className={styles.nav}
                        />

                        {/* Bottom: Tools/Status */}
                        <Flex
                            align="center"
                            justify="space-between"
                            className={styles.siderFooter}
                        >
                            <Flex gap={12}>
                                <Tooltip title={t('common.language')} placement="top">
                                    <span className={styles.siderAction} onClick={toggleLang}>
                                        {i18n.language.startsWith('zh') ? 'EN' : '中'}
                                    </span>
                                </Tooltip>
                                <Tooltip title="通知">
                                    <Badge count={0} size="small">
                                        <BellOutlined className={styles.siderAction} />
                                    </Badge>
                                </Tooltip>
                            </Flex>
                            <Flex align="center" gap={8}>
                                <span className={styles.statusText}>Online</span>
                                <div className={styles.statusDot} />
                            </Flex>
                        </Flex>
                    </Flex>
                </Sider>
            )}

            {/* === 主体区域 === */}
            <Layout className={styles.mainLayout}>
                {/* 右上角: 模式切换按钮 */}
                <div className={styles.modeSwitcher}>
                    <Tooltip title={isAIMode ? '切换到传统模式' : '切换到 AI 模式'} placement="bottomLeft">
                        <button
                            className={`${styles.modeSwitchBtn} ${isAIMode ? styles.modeSwitchAI : styles.modeSwitchClassic}`}
                            onClick={toggleViewMode}
                        >
                            {isAIMode ? (
                                <>
                                    <DesktopOutlined />
                                    <span className={styles.modeSwitchLabel}>传统模式</span>
                                </>
                            ) : (
                                <>
                                    <RobotOutlined />
                                    <span className={styles.modeSwitchLabel}>AI 模式</span>
                                </>
                            )}
                        </button>
                    </Tooltip>
                </div>

                {isAIMode ? (
                    /* 🤖 AI 模式: Chat 居中全屏 */
                    <Content className={styles.aiModeContent}>
                        <div className={styles.aiModeChatWrap}>
                            <ChatPanel />
                        </div>
                    </Content>
                ) : (
                    /* 📊 传统模式: Content + ChatPanel */
                    <>
                        <Content className={styles.content}>
                            <div className={styles.contentInner}>
                                <Outlet />
                            </div>
                        </Content>

                        {/* 右: AI Chat Panel (侧面板) */}
                        <div
                            className={styles.chatPanelWrap}
                            style={{ width: panelOpen ? panelWidth : 48 }}
                        >
                            <ChatPanel />
                        </div>
                    </>
                )}
            </Layout>

            {/* === 全局弹窗 (由 AI 触发) === */}
            <CreateKBModal
                open={isCreateKBModalOpen}
                onCancel={() => setCreateKBModalOpen(false)}
                onSubmit={handleCreateKB}
            />
        </Layout>
    );
};
