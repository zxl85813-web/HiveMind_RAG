/**
 * 🛰️ [HMER Phase 3] LLM Health Monitor
 * 核心健康度状态机：实时采集错误模式，触发降级熔断。
 */

export type HealthState = 'HEALTHY' | 'DEGRADED' | 'CRITICAL';

export interface HealthMetrics {
    consecutiveErrors: number;   // 连续失败次数 (429/5xx/Network)
    totalRequests: number;        // 总采样数
    rateLimitHits: number;        // 429 命中次数
    lastUpdated: number;          // 最后更新时间
}

export class LLMHealthMonitor {
    private state: HealthState = 'HEALTHY';
    private metrics: HealthMetrics = {
        consecutiveErrors: 0,
        totalRequests: 0,
        rateLimitHits: 0,
        lastUpdated: Date.now(),
    };

    /** 配置阈值 */
    private readonly THRESHOLDS = {
        DEGRADE_THRESHOLD: 5,     // 连续 5 次失败进入 DEGRADED
        CRITICAL_THRESHOLD: 10,    // 连续 10 次失败进入 CRITICAL (熔断)
        RATE_LIMIT_CRITICAL: 5,   // 连续 5 次 429 进入 CRITICAL (为 Chaos Test 留出空间)
    };

    /** 记录单次成功 */
    recordSuccess() {
        this.metrics.totalRequests++;
        this.metrics.consecutiveErrors = 0;
        this.metrics.rateLimitHits = 0;
        this.updateState();
    }

    /** 记录单次失败 */
    recordError(status?: number) {
        this.metrics.totalRequests++;
        this.metrics.consecutiveErrors++;
        
        if (status === 429) {
            this.metrics.rateLimitHits++;
        }

        this.updateState();
    }

    private updateState() {
        const prev = this.state;

        if (this.metrics.consecutiveErrors >= this.THRESHOLDS.CRITICAL_THRESHOLD || 
            this.metrics.rateLimitHits >= this.THRESHOLDS.RATE_LIMIT_CRITICAL) {
            this.state = 'CRITICAL';
        } else if (this.metrics.consecutiveErrors >= this.THRESHOLDS.DEGRADE_THRESHOLD) {
            this.state = 'DEGRADED';
        } else {
            this.state = 'HEALTHY';
        }

        if (prev !== this.state) {
            console.warn(`[LLMHealthMonitor] Provider State Changed: ${prev} -> ${this.state}`);
        }
    }

    /** 是否建议降级或重连 */
    shouldFallback(): boolean {
        return this.state === 'CRITICAL' || this.state === 'DEGRADED';
    }

    getState(): HealthState {
        return this.state;
    }

    getMetrics(): HealthMetrics {
        return { ...this.metrics };
    }

    /** 复位健康度 */
    reset() {
        this.metrics.consecutiveErrors = 0;
        this.metrics.rateLimitHits = 0;
        this.updateState();
    }
}

export const llmMonitor = new LLMHealthMonitor();
