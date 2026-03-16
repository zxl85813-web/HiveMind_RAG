import * as Sentry from "@sentry/react";
import { MonitorEventSchema, type MonitorEvent } from './schema/monitoring';
import type { AppError } from './AppError';

/**
 * 🛰️ [FE-GOV-002]: 全局监控与日志收口服务 (Sentry Integrated)
 */
class MonitorService {
    private isProd = import.meta.env.PROD;
    private dsn = import.meta.env.VITE_SENTRY_DSN;

    constructor() {
        if (this.dsn && this.dsn !== 'https://placeholder@sentry.io/4500000000000000') {
            this.initSentry();
        }
    }

    private initSentry() {
        Sentry.init({
            dsn: this.dsn,
            integrations: [
                Sentry.browserTracingIntegration(),
                Sentry.replayIntegration(),
            ],
            // Performance Monitoring
            tracesSampleRate: 1.0, 
            // Session Replay
            replaysSessionSampleRate: 0.1,
            replaysOnErrorSampleRate: 1.0,
            environment: import.meta.env.MODE,
        });
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

            // 2. Sentry 面包屑记录
            Sentry.addBreadcrumb({
                category: validatedEvent.category,
                message: validatedEvent.action,
                data: validatedEvent.metadata,
                level: "info",
            });

            // 3. TODO: 批量上报逻辑
        } catch (e) {
            console.warn('[Monitor] Failed to log event due to schema non-compliance', e);
        }
    }

    /** 记录错误 */
    public reportError(error: Error | AppError, metadata?: Record<string, unknown>) {
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

        // 生产环境或配置了 DSN 时上报 Sentry
        if (this.dsn) {
            Sentry.withScope((scope) => {
                scope.setTag("error_code", errorData.code);
                scope.setTag("layer", errorData.layer);
                scope.setExtra("metadata", { ...errorData.metadata, ...metadata });
                Sentry.captureException(error);
            });
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
