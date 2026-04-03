import { UnifiedLogSchema, type UnifiedLog, type MonitorEvent } from './schema/monitoring';
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
    private traceId: string = `fe-${Math.random().toString(36).substring(2, 15)}`;

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

    public getTraceId() {
        return this.traceId;
    }

    /** 记录标准事件 */
    public log(event: Omit<MonitorEvent, 'timestamp'>) {
        try {
            // 🛰️ [FE-GOV-002]: 统一映射到 UnifiedLog 契约
            const unifiedLog: UnifiedLog = {
                ts: Date.now(),
                level: event.category === 'error' ? 'ERROR' : 'INFO',
                trace_id: this.traceId,
                platform: 'FE',
                category: event.category,
                module: event.user_context?.page || 'UnknownUI',
                action: event.action,
                msg: event.label || event.action,
                meta: {
                    ...event.metadata,
                    value: event.value,
                },
                env: import.meta.env.MODE
            };

            const validatedLog = UnifiedLogSchema.parse(unifiedLog);

            // 1. 开发环境输出
            if (!this.isProd) {
                console.log(`[UnifiedLog][${validatedLog.level}][${this.traceId}] ${validatedLog.module} -> ${validatedLog.action}`, validatedLog);
            }

            // 2. Sentry 面包屑记录 (如果已加载)
            if (sentryInstance) {
                sentryInstance.addBreadcrumb({
                    category: validatedLog.category,
                    message: `${validatedLog.module}: ${validatedLog.action}`,
                    data: validatedLog.meta,
                    level: validatedLog.level.toLowerCase() as any,
                });
            }

            // 3. TODO: 批量上报逻辑 (P1)
        } catch (e) {
            console.warn('[Monitor] Failed to log event due to UnifiedLog non-compliance', e);
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
        const apiBase = import.meta.env.VITE_API_BASE_URL || '';
        const baseUrl = apiBase.replace(/\/+$/, '');
        const url = `${baseUrl}/telemetry`;
        const token = localStorage.getItem('access_token');
        
        const bodyContent = {
            type,
            payload,
            timestamp: new Date().toISOString(),
            context: {
                ua: navigator.userAgent,
                url: window.location.href,
                // [Architecture-Gate]: 在遥测中增加分组标识，避免 CI 混淆
                env: import.meta.env.MODE
            }
        };

        const body = JSON.stringify(bodyContent);

        // 🛰️ [Debug]: 在 CI 日志中区分 Dispatch 开始，方便 Playwright 同步
        console.log(`[Monitor] Dispatching business telemetry: ${type}`);

        try {
            // 使用 standard fetch + keepalive，确保即使页面卸载也能继续发送
            const response = await fetch(url, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body,
                keepalive: true,
                credentials: 'omit'
            });

            if (response.ok) {
                console.log(`[Monitor] Telemetry sent successfully: ${type}`);
            } else {
                console.warn(`[Monitor] Telemetry fetch rejected with status: ${response.status}. Falling back to sendBeacon.`);
                this.fallbackSendBeacon(url, body);
            }
        } catch (e) {
            console.warn(`[Monitor] Telemetry fetch error (likely page unload). Falling back to sendBeacon.`);
            this.fallbackSendBeacon(url, body);
        }
    }

    private fallbackSendBeacon(url: string, body: string) {
        if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
            const blob = new Blob([body], { type: 'application/json' });
            const success = navigator.sendBeacon(url, blob);
            if (success) {
                console.log(`[Monitor] Telemetry sent via fallback sendBeacon.`);
            }
        }
    }
}

export const monitor = new MonitorService();
