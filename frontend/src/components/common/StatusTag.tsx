/**
 * StatusTag — 统一状态标签组件。
 *
 * 将状态字符串映射为带图标+颜色的 Tag。
 * 用于 Agent 状态、任务状态、文档处理状态等。
 *
 * 用法:
 *   <StatusTag status="processing" />
 *   <StatusTag status="success" label="已完成" />
 *
 * @module components/common
 * @see REGISTRY.md > 前端 > 组件 > StatusTag
 */

import React from 'react';
import { Tag } from 'antd';
import {
    CheckCircleOutlined,
    SyncOutlined,
    ClockCircleOutlined,
    ExclamationCircleOutlined,
    CloseCircleOutlined,
    PauseCircleOutlined,
    ExperimentOutlined,
} from '@ant-design/icons';

type StatusType =
    | 'idle'
    | 'pending'
    | 'processing'
    | 'success'
    | 'warning'
    | 'error'
    | 'paused'
    | 'reflecting';

interface StatusConfig {
    icon: React.ReactNode;
    color: string;
    defaultLabel: string;
}

const statusConfigMap: Record<StatusType, StatusConfig> = {
    idle: { icon: <CheckCircleOutlined />, color: 'default', defaultLabel: '空闲' },
    pending: { icon: <ClockCircleOutlined />, color: 'default', defaultLabel: '等待中' },
    processing: { icon: <SyncOutlined spin />, color: 'processing', defaultLabel: '处理中' },
    success: { icon: <CheckCircleOutlined />, color: 'success', defaultLabel: '成功' },
    warning: { icon: <ExclamationCircleOutlined />, color: 'warning', defaultLabel: '警告' },
    error: { icon: <CloseCircleOutlined />, color: 'error', defaultLabel: '错误' },
    paused: { icon: <PauseCircleOutlined />, color: 'orange', defaultLabel: '已暂停' },
    reflecting: { icon: <ExperimentOutlined />, color: 'purple', defaultLabel: '自省中' },
};

export interface StatusTagProps {
    /** 状态类型 */
    status: StatusType;
    /** 自定义文字 (覆盖默认) */
    label?: string;
}

export const StatusTag: React.FC<StatusTagProps> = ({ status, label }) => {
    const config = statusConfigMap[status] || statusConfigMap.idle;
    return (
        <Tag icon={config.icon} color={config.color}>
            {label || config.defaultLabel}
        </Tag>
    );
};
