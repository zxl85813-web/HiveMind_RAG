import { prefetchConversation } from '../hooks/queries/useChatQuery';
import { chatApi } from '../services/chatApi';

/**
 * 🛰️ [HMER Phase 4] Intent Manager (意图预测管理器)
 * 职责：感知用户交互趋势，主动触发数据预加载 (Prefetching)。
 */

export type IntentType = 'chat' | 'knowledge' | 'settings' | 'graph' | 'dashboard' | 'audit' | 'security' | 'ai_warmup';

export interface PrefetchConfig {
    id?: string;
    priority?: 'high' | 'normal' | 'low';
    message?: string; // For AI Warmup probe
}

class IntentManager {
    private queryClient: any = null;
    private debounceTimers: Map<string, any> = new Map();

    /** 初始化，接入全局 QueryClient */
    init(client: any) {
        this.queryClient = client;
    }

    /** 
     * 预测意图：在 Hover 或 Focus 时调用 
     */
    predict(type: IntentType, options: PrefetchConfig = {}, delay: number = 200) {
        if (!this.queryClient) return;

        const key = `${type}-${options.id || 'all'}`;
        
        if (this.debounceTimers.has(key)) {
            clearTimeout(this.debounceTimers.get(key));
        }

        const timer = setTimeout(() => {
            this.executePrefetch(type, options);
            this.debounceTimers.delete(key);
        }, delay);

        this.debounceTimers.set(key, timer);
    }

    /** 取消预测 (Mouse Leave 时) */
    cancel(type: IntentType, options: PrefetchConfig = {}) {
        const key = `${type}-${options.id || 'all'}`;
        if (this.debounceTimers.has(key)) {
            clearTimeout(this.debounceTimers.get(key));
            this.debounceTimers.delete(key);
        }
    }

    /** 核心逻辑：分流至不同的 prefetch 策略 */
    private async executePrefetch(type: IntentType, options: PrefetchConfig) {
        if (!this.queryClient) return;

        console.log(`🚀 [Phase 4] Executing Intent: ${type}`, options);

        try {
            switch (type) {
                case 'chat':
                    if (options.id) {
                        await prefetchConversation(this.queryClient, options.id);
                    }
                    break;
                case 'ai_warmup':
                    // 🆕 [Phase 4.1]: Proactive Backend Warming (AI Probe)
                    if (options.message) {
                        chatApi.streamChat({
                            message: options.message,
                            is_prefetch: true,
                            onStatus: (status: any) => console.log(`🛰️ [Prefetch Status]: ${typeof status === 'string' ? status : JSON.stringify(status)}`),
                            onFinish: () => console.log(`✅ [Prefetch Done]`)
                        });
                    }
                    break;
                case 'knowledge':
                    // 1. 预取知识库列表 (React Query Cache)
                    await this.queryClient.prefetchQuery({
                        queryKey: ['knowledgeBases'],
                        staleTime: 60000
                    });
                    // 2. 🆕 [Phase 4.1]: 预热后端 AI 检索 (AI Probe)
                    // 当用户进入知识库页面时，大概率会提问有关资产、上传或搜索的问题
                    chatApi.streamChat({
                        message: "如何管理和搜索我上传的知识资产？",
                        is_prefetch: true
                    });
                    break;
                case 'dashboard':
                    // 预取仪表盘统计
                    await this.queryClient.prefetchQuery({
                        queryKey: ['dashboardStats'],
                        staleTime: 30000
                    });
                    break;
                case 'audit':
                    // 预取审计日志
                    await this.queryClient.prefetchQuery({
                        queryKey: ['auditLogs'],
                        staleTime: 60000
                    });
                    break;
                default:
                    break;
            }
        } catch (err) {
            console.warn(`[Phase 4] Prefetch was cancelled or failed for ${type}:`, err);
        }
    }
}

export const intentManager = new IntentManager();
