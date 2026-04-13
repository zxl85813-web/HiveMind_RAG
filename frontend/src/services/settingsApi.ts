/**
 * Settings API — 平台设置接口。
 *
 * 管理平台内置知识库 (platform_knowledge.yaml)。
 *
 * @module services
 */

import api from './api';
import type { ApiResponse } from '../types';

export interface PlatformKnowledge {
    overview: string;
    features: PlatformFeature[];
    faq: FAQItem[];
}

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

export interface ModelMetadata {
    id: string;
    name: string;
    provider: string;
    input_price_1m: number;
    output_price_1m: number;
    characteristics: string[];
    usage_scenarios: string[];
    status: string;
}

export interface GovernanceInsight {
    type: 'cost' | 'performance' | 'strategy';
    title: string;
    content: string;
    priority: 'low' | 'medium' | 'high';
}

export interface LLMGovernanceConfig {
    tier_mapping: {
        simple: string;
        medium: string;
        complex: string;
        reasoning: string;
    };
    model_registry: ModelMetadata[];
    priority_strategies: Record<string, any>;
    budget_daily_limit: number;
    dialect_enabled: boolean;
}


export const settingsApi = {
    /** 获取平台知识库 */
    getPlatformKnowledge: () =>
        api.get<ApiResponse<PlatformKnowledge>>('/settings/platform-knowledge'),

    /** 整体更新平台知识库 */
    updatePlatformKnowledge: (data: PlatformKnowledge) =>
        api.put<ApiResponse<PlatformKnowledge>>('/settings/platform-knowledge', data),

    /** 获取 LLM 治理配置 (L5) */
    getLlmGovernance: () =>
        api.get<ApiResponse<LLMGovernanceConfig>>('/settings/llm/llm-governance'),

    /** 更新 LLM 治理配置 (L5) */
    updateLlmGovernance: (data: LLMGovernanceConfig) =>
        api.put<ApiResponse<LLMGovernanceConfig>>('/settings/llm/llm-governance', data),

    /** 获取治理洞察与建议 */
    getAdaptiveInsights: () =>
        api.get<ApiResponse<GovernanceInsight[]>>('/settings/llm/llm-governance/insights'),

    /** 获取智体提报任务 (L5 Governance Tasks) */
    getGovernanceTasks: () =>
        api.get<ApiResponse<any[]>>('/settings/llm/governance/tasks'),
};

