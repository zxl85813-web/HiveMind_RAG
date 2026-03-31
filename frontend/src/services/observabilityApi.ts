import api from './api';
import type { ApiResponse } from '../types';

/**
 * [M7.1] LLM 模型性能与路由健康度
 */
export interface LLMMetric {
    model_name: string;
    provider: string;
    avg_latency: number;
    success_rate: number;
    total_calls: number;
    total_tokens: number;
    cost?: number;
}

export const observabilityApi = {
    /** 获取 LLM 模型性能与路由监控数据 */
    getLLMMetrics: (days = 1) => 
        api.get<ApiResponse<LLMMetric[]>>(`/observability/llm-metrics?days=${days}`),

    /** 获取服务治理完整快照 (包含了降级、熔断、限流、路由、情节记忆等) */
    getServiceGovernance: () =>
        api.get<ApiResponse<any>>('/observability/service-governance'),

    /** 获取 RAG 追踪列表 */
    getTraces: (params: { kb_id?: string; limit?: number } = {}) =>
        api.get<ApiResponse<any[]>>('/observability/traces', { params }),

    /** 获取检索质量指标 */
    getRetrievalQuality: (params: { kb_id?: string; days?: number } = {}) =>
        api.get<ApiResponse<any>>('/observability/retrieval-quality', { params }),

    /** 获取热门查询分析 */
    getHotQueries: (params: { kb_id?: string; limit?: number; days?: number } = {}) =>
        api.get<ApiResponse<any[]>>('/observability/hot-queries', { params }),

    /** 获取冷门/低效文档分析 */
    getColdDocuments: (kbId: string, params: { limit?: number; days?: number } = {}) =>
        api.get<ApiResponse<any[]>>(`/observability/cold-documents/${kbId}`, { params }),
};
