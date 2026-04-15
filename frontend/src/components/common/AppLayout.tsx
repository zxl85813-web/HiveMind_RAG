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
    DeploymentUnitOutlined,
    RobotOutlined,
    DesktopOutlined,
    ExperimentOutlined,
    DashboardOutlined,
    AreaChartOutlined,
    NodeIndexOutlined,
    SearchOutlined,
    LogoutOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useChatStore } from '../../stores/chatStore';
import { useAuthStore } from '../../stores/authStore';
import { ChatPanel } from '../chat/ChatPanel';
import { CreateKBModal } from '../knowledge/CreateKBModal';
import { useCreateKnowledgeBase } from '../../hooks/useDashboardData';
import { appRoutes } from '../../config/appRoutes';
import type { CreateKnowledgeBaseParams } from '../../services/knowledgeApi';
import { intentManager, type IntentType } from '../../core/IntentManager';
import styles from './AppLayout.module.css';

const { Sider, Content } = Layout;

/** 路由路径到意图类型的映射 */
const routeIntentMap: Record<string, IntentType> = {
    '/': 'dashboard',
    '/knowledge': 'knowledge',
    '/audit': 'audit',
    '/security': 'security',
};

export const AppLayout: React.FC = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const { message } = App.useApp();
    const hasAccess = useAuthStore((state) => state.hasAccess);
    const profile = useAuthStore((state) => state.profile);

    const [collapsed, setCollapsed] = React.useState(false);
    const [openKeys, setOpenKeys] = React.useState<string[]>([]);
    const activeKey = location.pathname;

    useEffect(() => {
        const currentRoute = appRoutes.find(r => r.path === activeKey);
        if (currentRoute?.category) {
            setOpenKeys(prev => {
                const key = `cat-${currentRoute.category}`;
                return prev.includes(key) ? prev : [...prev, key];
            });
        }
    }, [activeKey]);

    // 🔍 [Diagnostic]: Log profile to help debug permission issues
    console.log('[AppLayout] Current Profile:', profile);
    console.log('[AppLayout] Profile Roles:', profile.roles);
    console.log('[AppLayout] Admin Status:', profile.roles.includes('admin'));

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

    const iconMap: Record<string, React.ReactNode> = {
        AppstoreOutlined: <AppstoreOutlined />,
        DatabaseOutlined: <DatabaseOutlined />,
        ClusterOutlined: <ClusterOutlined />,
        BulbOutlined: <BulbOutlined />,
        SettingOutlined: <SettingOutlined />,
        SafetyCertificateOutlined: <SafetyCertificateOutlined />,
        RocketOutlined: <RocketOutlined />,
        LockOutlined: <LockOutlined />,
        LineChartOutlined: <LineChartOutlined />,
        FolderOpenOutlined: <FolderOpenOutlined />,
        SisternodeOutlined: <SisternodeOutlined />,
        DeploymentUnitOutlined: <DeploymentUnitOutlined />,
        ExperimentOutlined: <ExperimentOutlined />,
        DashboardOutlined: <DashboardOutlined />,
        AreaChartOutlined: <AreaChartOutlined />,
        NodeIndexOutlined: <NodeIndexOutlined />,
        SearchOutlined: <SearchOutlined />,
    };

    /** 
     * 🛰️ [Nav-Hardening]: 菜单项归类重构 (DEC-260413-NAV)
     * 将平铺的路由按照治理域进行聚合，提升系统可解释性。
     */
    const groupedRoutes = appRoutes
        .filter((route) => route.showInMenu && hasAccess(route.access))
        .reduce((acc, route) => {
            const cat = route.category || 'insight';
            if (!acc[cat]) acc[cat] = [];
            acc[cat].push(route);
            return acc;
        }, {} as Record<string, typeof appRoutes>);

    const categoryOrder: Array<'insight' | 'cognitive' | 'studio' | 'lab' | 'observability' | 'sovereign' | 'system'> = [
        'insight', 'cognitive', 'studio', 'lab', 'observability', 'sovereign', 'system'
    ];

    const navItems = categoryOrder.map(cat => {
        const routes = groupedRoutes[cat];
        if (!routes || routes.length === 0) return null;

        // 如果该分类下只有一个项（如概览），则直接渲染为菜单项
        if (cat === 'insight' && routes.length === 1) {
            const route = routes[0];
            const intent = routeIntentMap[route.path];
            return {
                key: route.path,
                label: (
                    <div 
                        onMouseEnter={intent ? () => intentManager.predict(intent) : undefined}
                        onMouseLeave={intent ? () => intentManager.cancel(intent) : undefined}
                    >
                        {t(route.labelKey)}
                    </div>
                ),
                icon: iconMap[route.icon] || <AppstoreOutlined />,
            };
        }

        // 其他分类渲染为 SubMenu (可收缩文件夹)
        return {
            key: `cat-${cat}`,
            label: t(`nav.category.${cat}`),
            icon: cat === 'cognitive' ? <DatabaseOutlined /> : 
                  cat === 'studio' ? <ExperimentOutlined /> :
                  cat === 'lab' ? <LineChartOutlined /> :
                  cat === 'observability' ? <NodeIndexOutlined /> :
                  cat === 'sovereign' ? <SafetyCertificateOutlined /> :
                  cat === 'system' ? <SettingOutlined /> : 
                  <AppstoreOutlined />,
            children: routes.map((route) => {
                const intent = routeIntentMap[route.path];
                return {
                    key: route.path,
                    label: (
                        <div 
                            onMouseEnter={intent ? () => intentManager.predict(intent) : undefined}
                            onMouseLeave={intent ? () => intentManager.cancel(intent) : undefined}
                        >
                            {t(route.labelKey)}
                        </div>
                    ),
                    icon: iconMap[route.icon] || <AppstoreOutlined />,
                };
            }),
        };
    }).filter(Boolean);

    console.log('[AppLayout] Grouped Routes:', groupedRoutes);
    console.log('[AppLayout] Final Nav Items:', navItems);

    const toggleLang = () => {
        const current = i18n.language;
        const next = current.startsWith('zh') ? 'en-US' : 'zh-CN';
        i18n.changeLanguage(next);
    };

    /** 路由变化时更新 Chat 上下文 */
    useEffect(() => {
        updateContext(location.pathname);
    }, [location.pathname, updateContext]);

    /** 处理退出登录 */
    const handleLogout = () => {
        useAuthStore.getState().setAuthenticated(false);
        navigate('/login');
    };

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
                <Sider 
                    width={240} 
                    className={styles.sider} 
                    theme="dark" 
                    collapsible 
                    collapsed={collapsed} 
                    onCollapse={(value) => setCollapsed(value)}
                >
                    <Flex vertical className={styles.siderInner}>
                        <div className={styles.logo} onClick={() => {
                            useChatStore.getState().setViewMode('ai');
                            navigate('/');
                        }}>
                            <span className={styles.logoMark}>⬡</span>
                            {!collapsed && <span className={styles.logoText}>HiveMind</span>}
                        </div>
                        <Menu
                            mode="inline"
                            selectedKeys={[activeKey]}
                            openKeys={openKeys}
                            onOpenChange={(keys) => setOpenKeys(keys)}
                            onClick={handleNavClick}
                            items={navItems}
                            className={styles.nav}
                        />
                        <Flex 
                            align="center" 
                            justify={collapsed ? "center" : "space-between"} 
                            className={styles.siderFooter}
                            vertical={collapsed}
                            gap={collapsed ? 16 : 0}
                        >
                            <Flex gap={12} vertical={collapsed} align="center">
                                <Tooltip title={t('common.language')} placement="right">
                                    <span className={styles.siderAction} onClick={toggleLang}>
                                        {i18n.language.startsWith('zh') ? 'EN' : '中'}
                                    </span>
                                </Tooltip>
                                <Badge count={0} size="small" offset={[-4, 4]}>
                                    <BellOutlined className={styles.siderAction} />
                                </Badge>
                                <Tooltip title="退出登录" placement="right">
                                    <LogoutOutlined className={styles.siderAction} onClick={handleLogout} />
                                </Tooltip>
                            </Flex>
                            {!collapsed && (
                                <Flex align="center" gap={8}>
                                    <span className={styles.statusText}>{profile.roles[0]?.toUpperCase() || 'UNKNOWN'}</span>
                                    <div className={styles.statusDot} />
                                </Flex>
                            )}
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
