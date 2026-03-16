import { z } from 'zod';

/**
 * 🛰️ [FE-GOV-002]: Schema-Driven 错误体系
 * 
 * 定义系统中所有可能的异常分类与结构
 */

export const ErrorSeveritySchema = z.enum(['low', 'medium', 'high', 'critical']);
export type ErrorSeverity = z.infer<typeof ErrorSeveritySchema>;

export const ErrorLayerSchema = z.enum(['api', 'ui', 'rendering', 'auth', 'resource', 'business']);
export type ErrorLayer = z.infer<typeof ErrorLayerSchema>;

/** 标准错误结构 */
export const AppErrorSchema = z.object({
    code: z.string(), // 错误代码，如 'API_AUTH_FAILED'
    message: z.string(), // 用户友好的错误描述
    layer: ErrorLayerSchema, // 故障发生的层级
    severity: ErrorSeveritySchema, // 严重程度
    metadata: z.record(z.string(), z.unknown()).optional(), // 辅助调试的元数据
    stack: z.string().optional(), // 堆栈信息
    timestamp: z.number(),
});

export type AppErrorPayload = z.infer<typeof AppErrorSchema>;

/** 系统异常代码枚举 */
export const ErrorCode = {
    // API 层
    API_UNAUTHORIZED: 'API_UNAUTHORIZED',
    API_FORBIDDEN: 'API_FORBIDDEN',
    API_NETWORK_ERROR: 'API_NETWORK_ERROR',
    API_TIMEOUT: 'API_TIMEOUT',
    API_MALFORMED_DATA: 'API_MALFORMED_DATA',

    // UI & Rendering 层
    UI_RENDER_CRASH: 'UI_RENDER_CRASH',
    UI_COMPONENT_ERROR: 'UI_COMPONENT_ERROR',

    // 业务层
    BIZ_FILE_TOO_LARGE: 'BIZ_FILE_TOO_LARGE',
    BIZ_INVALID_KB_NAME: 'BIZ_INVALID_KB_NAME',

    // 通用
    UNKNOWN_ERROR: 'UNKNOWN_ERROR',
} as const;
