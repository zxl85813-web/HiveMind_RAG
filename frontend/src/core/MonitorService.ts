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

    /** 记录性能指标 */
    public trackPerformance(metric: string, value: number, tags?: Record<string, string>) {
        if (this.isProd) {
            // Sentry 性能监控逻辑
            console.log(`[Performance] ${metric}: ${value}ms`, tags);
        }
    }
}

export const monitor = new MonitorService();
