import api from '../services/api';

export interface MetricSummary {
    count: number;
    mean: number;
    p50: number;
    p95: number;
    max: number;
}

class BaselineProbe {
    private rawData: { name: string; value: number; context?: any }[] = [];
    private isEnabled = import.meta.env.DEV || true;
    private sessionId = Math.random().toString(36).substring(2, 15);
    private flushTimer: any = null;
    
    // 🛰️ [HMER Phase 0.5]: A/B 测试与版本追踪
    private appVersion = '0.1.0'; // 应从 package.json 或 env 获取
    private experimentId = localStorage.getItem('HMER_EXP_ID') || 'baseline';
    private experimentGroup = localStorage.getItem('HMER_EXP_GROUP') || 'control'; // control | experiment

    /** 记录一个时间戳刻度 */
    mark(name: string) {
        if (!this.isEnabled) return;
        performance.mark(name);
    }

    /** 测量两个刻度间的间隔并记录 */
    measure(name: string, startMark: string, endMark: string, context?: any) {
        if (!this.isEnabled) return;
        try {
            performance.measure(name, startMark, endMark);
            const entries = performance.getEntriesByName(name, 'measure');
            const lastEntry = entries[entries.length - 1];
            if (lastEntry) {
                this.record(name, lastEntry.duration, context);
            }
        } catch {
            // 忽略由于 mark 丢失导致的错误
        }
    }

    /** 直接记录数值指标 */
    record(name: string, value: number, context?: any) {
        if (!this.isEnabled) return;
        
        // 自动注入版本与 A/B 组标
        const payload = { 
            name, 
            value, 
            context: {
                ...context,
                v: this.appVersion,
                exp: this.experimentId,
                grp: this.experimentGroup
            } 
        };

        this.rawData.push(payload);
        
        // 低频日志
        if (this.rawData.length % 5 === 0) {
            console.debug(`[Baseline] ${name}: ${value.toFixed(2)}ms (Batch: ${this.rawData.length})`);
        }

        // 自动上报逻辑：满 10 条或 30 秒上报一次
        this.scheduleFlush();
    }

    private scheduleFlush() {
        if (this.flushTimer) return;
        
        if (this.rawData.length >= 10) {
            this.reportToServer();
        } else {
            this.flushTimer = setTimeout(() => this.reportToServer(), 30000);
        }
    }

    /** 将采集到的基线数据发送至后端接收站点 */
    async reportToServer() {
        if (this.rawData.length === 0) return;

        const payload = {
            metrics: [...this.rawData],
            session_id: this.sessionId
        };
        
        this.rawData = []; // 立即清空，防止重入
        if (this.flushTimer) {
            clearTimeout(this.flushTimer);
            this.flushTimer = null;
        }

        try {
            // 优先使用 api.post (走权限验证)，如果页面关闭可由于 api 的 axios 实例可能被销毁，
            // 极端情况可用 navigator.sendBeacon
            await api.post('/observability/baseline', payload);
        } catch (error) {
            console.warn('[Baseline] Failed to sync baseline to backend', error);
        }
    }

    /** 输出表格报告 (本地预览) */
    printReport() {
        console.group('📊 HiveMind Phase 0 Baseline (Local Queue)');
        console.table(this.rawData);
        console.info('Tip: 后端聚合报告请访问 API: /api/v1/observability/baseline-report');
        console.groupEnd();
    }
}

export const baseline = new BaselineProbe();

// 全局暴露以供调试
if (typeof window !== 'undefined') {
    (window as any).__BASELINE__ = baseline;
    window.addEventListener('beforeunload', () => {
        baseline.reportToServer();
    });
}
