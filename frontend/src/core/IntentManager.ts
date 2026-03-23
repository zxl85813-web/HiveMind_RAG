import { prefetchConversation } from '../hooks/queries/useChatQuery';

/**
 * 🛰️ [HMER Phase 4] Intent Manager (意图预测管理器)
 * 职责：感知用户交互趋势，主动触发数据预加载 (Prefetching)。
 */

export type IntentType = 'chat' | 'knowledge' | 'settings' | 'graph';

export interface PrefetchConfig {
    id?: string;
    priority?: 'high' | 'normal' | 'low';
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
    predict(type: IntentType, options: PrefetchConfig = {}, delay: number = 150) {
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
                        // 😂 [Phase 4] 预热特定会话：
                        // 在用户点击之前，消息记录已经静默加载到 React Query 缓存中
                        await prefetchConversation(this.queryClient, options.id);
                    }
                    break;
                case 'knowledge':
                    // 未来可以集成知识库预热
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
