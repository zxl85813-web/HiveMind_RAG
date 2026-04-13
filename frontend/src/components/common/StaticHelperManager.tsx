import React from 'react';
import { App } from 'antd';
import { setStaticHelpers } from '../../core/antdStatic';

/**
 * 🛰️ [FE-GOV]: Ant Design Static Helper Manager
 * 职责: 将 AntD App 组件提供的实例桥接到 vanilla JS 模块。
 */
export const StaticHelperManager: React.FC = () => {
    const { message, notification, modal } = App.useApp();

    // 这一步是关键：将 hooks 提供的实例暴露给全局静态变量
    setStaticHelpers(message, notification, modal);

    return null; // 这是一个纯逻辑组件，不渲染任何 UI
};
