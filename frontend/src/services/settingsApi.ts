/**
 * Settings API — 平台设置接口。
 *
 * 管理平台内置知识库 (platform_knowledge.yaml)。
 *
 * @module services
 */

import api from './api';

// === 类型定义 ===

export interface PlatformFeature {
    name: string;
    path: string;
    description: string;
    operations: string[];
}

export interface FAQItem {
    q: string;
    a: string;
}

export interface PlatformKnowledge {
    overview: string;
    features: PlatformFeature[];
    faq: FAQItem[];
}

// === API 函数 ===

export const settingsApi = {
    /** 获取平台知识库 */
    getPlatformKnowledge: () =>
        api.get<PlatformKnowledge>('/settings/platform-knowledge'),

    /** 整体更新平台知识库 */
    updatePlatformKnowledge: (data: PlatformKnowledge) =>
        api.put<PlatformKnowledge>('/settings/platform-knowledge', data),

    /** 添加功能模块 */
    addFeature: (feature: PlatformFeature) =>
        api.post<PlatformFeature>('/settings/platform-knowledge/features', feature),

    /** 删除功能模块 */
    deleteFeature: (name: string) =>
        api.delete(`/settings/platform-knowledge/features/${encodeURIComponent(name)}`),

    /** 添加 FAQ */
    addFaq: (faq: FAQItem) =>
        api.post<FAQItem>('/settings/platform-knowledge/faq', faq),

    /** 删除 FAQ */
    deleteFaq: (index: number) =>
        api.delete(`/settings/platform-knowledge/faq/${index}`),
};
