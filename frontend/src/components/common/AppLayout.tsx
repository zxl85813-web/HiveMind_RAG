/**
 * AppLayout — AI-First 全局布局。
 *
 * 结构: Header + (Content | ChatPanel)
 * Chat Panel 永驻右侧，页面内容在左侧。
 * Header 上不再有"对话"入口 (chat 不再是 page)。
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
    RocketOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useChatStore } from '../../stores/chatStore';
import { ChatPanel } from '../chat/ChatPanel';
import styles from './AppLayout.module.css';

const { Sider, Content } = Layout;

/** 导航项 (去掉了"对话"— 因为 Chat 是面板不是页面) */
const navItems = [
    { key: '/', label: '概览', icon: <AppstoreOutlined /> },
    { key: '/knowledge', label: '知识库', icon: <DatabaseOutlined /> },
    { key: '/studio', label: '创作', icon: <RocketOutlined /> },
    { key: '/agents', label: 'Agents', icon: <ClusterOutlined /> },
    { key: '/learning', label: '动态', icon: <BulbOutlined /> },
    { key: '/settings', label: '设置', icon: <SettingOutlined /> },
];

export const AppLayout: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { panelOpen, panelWidth, updateContext } = useChatStore();

    /** 路由变化时更新 Chat 上下文 */
    useEffect(() => {
        updateContext(location.pathname);
    }, [location.pathname, updateContext]);

    /** 当前活跃路由 */
    const activeKey = location.pathname === '/'
        ? '/'
        : '/' + (location.pathname.split('/')[1] || '');

    return (
        <Layout className={styles.layout}>
            {/* === 左侧全局导航 Sider === */}
            <Sider
                width={240}
                className={styles.sider}
                theme="dark"
            >
                <Flex vertical className={styles.siderInner}>
                    {/* Top: Logo */}
                    <div className={styles.logo} onClick={() => navigate('/')}>
                        <span className={styles.logoMark}>⬡</span>
                        <span className={styles.logoText}>HiveMind</span>
                    </div>

                    {/* Middle: Nav Menu */}
                    <Menu
                        mode="inline"
                        selectedKeys={[activeKey]}
                        onClick={({ key }) => navigate(key)}
                        items={navItems}
                        className={styles.nav}
                    />

                    {/* Bottom: Tools/Status */}
                    <Flex align="center" justify="space-between" className={styles.siderFooter}>
                        <Tooltip title="通知">
                            <Badge count={0} size="small">
                                <BellOutlined className={styles.siderAction} />
                            </Badge>
                        </Tooltip>
                        <Flex align="center" gap={8}>
                            <span className={styles.statusText}>All Systems Online</span>
                            <div className={styles.statusDot} />
                        </Flex>
                    </Flex>
                </Flex>
            </Sider>

            {/* === 主体区域: Content + ChatPanel === */}
            <Layout className={styles.mainLayout}>
                {/* 左: 页面内容 */}
                <Content className={styles.content}>
                    <div className={styles.contentInner}>
                        <Outlet />
                    </div>
                </Content>

                {/* 右: AI Chat Panel */}
                <div
                    className={styles.chatPanelWrap}
                    style={{ width: panelOpen ? panelWidth : 48 }}
                >
                    <ChatPanel />
                </div>
            </Layout>
        </Layout>
    );
};
