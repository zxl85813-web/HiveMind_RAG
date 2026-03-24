import { MonitorEventSchema, type MonitorEvent } from './schema/monitoring';
import type { AppError } from './AppError';

// 🚀 [Architecture-Optimization]: Sentry Lazy Loading
// Use dynamic imports to keep Sentry out of the main bundle.
let sentryInstance: typeof import("@sentry/react") | null = null;

/**
 * 🛰️ [FE-GOV-002]: 全局监控与日志收口服务 (Sentry Lazy Integrated)
 */
class MonitorService {
    private isProd = import.meta.env.PROD;
    private dsn = import.meta.env.VITE_SENTRY_DSN;
    private initPromise: Promise<void> | null = null;

    constructor() {
        if (this.dsn && this.dsn !== 'https://placeholder@sentry.io/4500000000000000') {
            void this.ensureSentry();
        }
    }

    private async ensureSentry() {
        if (sentryInstance) return;
        if (this.initPromise) return this.initPromise;

        this.initPromise = (async () => {
            try {
                const Sentry = await import("@sentry/react");
                sentryInstance = Sentry;
                
                Sentry.init({
                    dsn: this.dsn,
                    integrations: [
                        Sentry.browserTracingIntegration(),
                        Sentry.replayIntegration(),
                    ],
                    tracesSampleRate: 1.0, 
                    replaysSessionSampleRate: 0.1,
                    replaysOnErrorSampleRate: 1.0,
                    environment: import.meta.env.MODE,
                });
            } catch (err) {
                console.error('[Monitor] Failed to load Sentry', err);
            }
        })();
        
        return this.initPromise;
    }

    /** 记录标准事件 */
    public log(event: Omit<MonitorEvent, 'timestamp'>) {
        try {
            const validatedEvent = MonitorEventSchema.parse({
                ...event,
                timestamp: Date.now()
            });

            // 1. 开发环境输出
            if (!this.isProd) {
                console.log(`[Monitor][${validatedEvent.category}] ${validatedEvent.action}`, validatedEvent);
            }

            // 2. Sentry 面包屑记录 (如果已加载)
            if (sentryInstance) {
                sentryInstance.addBreadcrumb({
                    category: validatedEvent.category,
                    message: validatedEvent.action,
                    data: validatedEvent.metadata,
                    level: "info",
                });
            }

            // 3. TODO: 批量上报逻辑
        } catch (e) {
            console.warn('[Monitor] Failed to log event due to schema non-compliance', e);
        }
    }

    /** 记录错误 */
    public async reportError(error: Error | AppError, metadata?: Record<string, unknown>) {
        const errorData = (error as any).payload || {
            code: 'UNKNOWN_ERROR',
            message: error.message,
            layer: 'ui',
            severity: 'medium',
            stack: error.stack
        };

        this.log({
            category: 'error',
            action: errorData.code,
            metadata: {
                ...errorData,
                ...metadata
            }
        });

        // 确保 Sentry 已加载 (如果是错误上报，值得等待)
        if (this.dsn) {
            await this.ensureSentry();
            if (sentryInstance) {
                sentryInstance.withScope((scope) => {
                    scope.setTag("error_code", errorData.code);
                    scope.setTag("layer", errorData.layer);
                    scope.setExtra("metadata", { ...errorData.metadata, ...metadata });
                    sentryInstance!.captureException(error);
                });
            }
        }
    }

    /** 
     * 🛰️ [Architecture-Gate]: 鲁棒性的遥测上报
     * 用于页面即将关闭、崩溃或流式任务突然终止时，确保指标能送达后端
     */
    public async dispatchBeacon(type: string, payload: any) {
        // 🛰️ [Architecture-Gate]: 确保在 CI 环境下 URL 拼接逻辑稳健
        const apiBase = import.meta.env.VITE_API_BASE_URL || '';
        const baseUrl = apiBase.replace(/\/+$/, '');
        const url = `${baseUrl}/telemetry`;
        
        const body = JSON.stringify({
            type,
            payload,
            timestamp: new Date().toISOString(),
            context: {
                ua: navigator.userAgent,
                url: window.location.href
            }
        });

        console.log(`[Monitor] Dispatching telemetry: ${url} (Type: ${type})`);

        try {
            // 使用 standard fetch + keepalive，它是目前最可靠的离屏发送方案
            await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body,
                keepalive: true,
                credentials: 'omit'
            });
            console.log(`[Monitor] Telemetry sent: ${type}`);
        } catch (e) {
            // 临终救赎：如果是页面卸载导致的失败，尝试最后一线生机
            if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
                const blob = new Blob([body], { type: 'application/json' });
                navigator.sendBeacon(url, blob);
            }
        }
    }
}

export const monitor = new MonitorService();
