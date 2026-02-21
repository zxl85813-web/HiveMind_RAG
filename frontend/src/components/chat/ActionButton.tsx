/**
 * ActionButton — AI 操作按钮。
 *
 * AI 回答中嵌入的可交互按钮，点击后执行对应操作:
 *   - navigate → 跳转到指定页面
 *   - open_modal → 打开弹窗
 *   - execute → 调用后端接口
 *
 * @module components/chat
 * @see docs/design/ai-first-frontend.md
 */

import React from 'react';
import { Button } from 'antd';
import {
    ArrowRightOutlined,
    DatabaseOutlined,
    ClusterOutlined,
    PlusOutlined,
    UploadOutlined,
    UnorderedListOutlined,
    ExperimentOutlined,
    BulbOutlined,
    SettingOutlined,
    SearchOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { AIAction } from '../../types';
import { useChatStore } from '../../stores/chatStore';

/** 图标名称 → 组件映射 */
const iconMap: Record<string, React.ReactNode> = {
    DatabaseOutlined: <DatabaseOutlined />,
    ClusterOutlined: <ClusterOutlined />,
    PlusOutlined: <PlusOutlined />,
    UploadOutlined: <UploadOutlined />,
    UnorderedListOutlined: <UnorderedListOutlined />,
    ExperimentOutlined: <ExperimentOutlined />,
    BulbOutlined: <BulbOutlined />,
    SettingOutlined: <SettingOutlined />,
    SearchOutlined: <SearchOutlined />,
    ArrowRightOutlined: <ArrowRightOutlined />,
};

interface ActionButtonProps {
    action: AIAction;
}

export const ActionButton: React.FC<ActionButtonProps> = ({ action }) => {
    const navigate = useNavigate();
    const executeAction = useChatStore((s) => s.executeAction);

    const handleClick = () => {
        const navTarget = executeAction(action);
        if (navTarget) {
            navigate(navTarget);
        }
    };

    return (
        <Button
            type={action.variant === 'primary' ? 'primary' : action.variant === 'link' ? 'link' : 'default'}
            size="small"
            icon={action.icon ? iconMap[action.icon] : <ArrowRightOutlined />}
            onClick={handleClick}
        >
            {action.label}
        </Button>
    );
};
