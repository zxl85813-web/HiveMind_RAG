import { AppErrorSchema, type AppErrorPayload } from './schema/error';

/**
 * 🛰️ [FE-GOV-002]: 系统标准异常类
 */
export class AppError extends Error {
    public readonly payload: AppErrorPayload;

    constructor(data: Omit<AppErrorPayload, 'timestamp' | 'stack'>) {
        super(data.message);
        this.name = 'AppError';
        
        this.payload = AppErrorSchema.parse({
            ...data,
            stack: this.stack,
            timestamp: Date.now(),
        });

        // 捕获堆栈 (V8 specific)
        if ((Error as any).captureStackTrace) {
            (Error as any).captureStackTrace(this, AppError);
        }
    }

    /** 工厂方法：从 API 响应创建错误 */
    static fromApiResponse(message: string, code: string, metadata?: Record<string, unknown>): AppError {
        return new AppError({
            code,
            message,
            layer: 'api',
            severity: 'medium',
            metadata
        });
    }

    /** 工厂方法：UI 渲染崩溃 */
    static fromCrash(err: Error, metadata?: Record<string, unknown>): AppError {
        return new AppError({
            code: 'UI_RENDER_CRASH',
            message: err.message,
            layer: 'rendering',
            severity: 'high',
            metadata: {
                ...metadata,
                originalName: err.name
            }
        });
    }
}
