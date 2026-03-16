import type { z } from 'zod';
import { AppError } from '../core/AppError';
import { monitor } from '../core/MonitorService';
import { ErrorCode } from '../core/schema/error';

/**
 * 🛰️ [FE-GOV-002]: Schema-Driven 数据流保护
 * 
 * 在数据进入业务层前进行强制 Schema 校验，防止后端返回字段漂移。
 */
export async function safeValidate<T>(
    schema: z.ZodSchema<T>,
    data: unknown,
    context: { apiName: string; layer?: string }
): Promise<T> {
    const result = schema.safeParse(data);

    if (!result.success) {
        const errorMsg = `[Schema Drift] API ${context.apiName} returned unexpected data structure.`;
        
        const appError = new AppError({
            code: ErrorCode.API_MALFORMED_DATA,
            message: errorMsg,
            layer: (context.layer as any) || 'api',
            severity: 'high',
            metadata: {
                apiName: context.apiName,
                zodErrors: result.error.issues,
                receivedData: data
            }
        });

        // 自动上报监控
        monitor.reportError(appError);

        // 开发环境下直接 throw 方便调试
        if (import.meta.env.DEV) {
            console.error(errorMsg, result.error.format());
        }

        // 生产环境下返回解析成功的部分或抛出异常，这里选择抛出以进入 ErrorBoundary
        throw appError;
    }

    return result.data;
}
