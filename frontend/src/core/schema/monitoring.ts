import { z } from 'zod';

/** 🛰️ [FE-GOV-002]: 全链路统一日志协议 */

export const LogLevelSchema = z.enum(['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']);
export type LogLevel = z.infer<typeof LogLevelSchema>;

export const EventCategorySchema = z.enum(['user_action', 'performance', 'error', 'system']);
export type EventCategory = z.infer<typeof EventCategorySchema>;

/** 🛰️ [FE-GOV-002]: 统一日志契约 (Cross-Platform) */
export const UnifiedLogSchema = z.object({
    ts: z.string().datetime().or(z.number()), // 支持 ISO 字符串或毫秒时间戳
    level: LogLevelSchema,
    trace_id: z.string().optional(),
    platform: z.enum(['FE', 'BE']),
    category: EventCategorySchema,
    module: z.string(), // 具体模块，如 'ChatPanel', 'RAGGateway'
    action: z.string(), // 操作名称
    msg: z.string(), // 详细描述
    meta: z.record(z.string(), z.any()).optional(),
    env: z.string(),
});

export type UnifiedLog = z.infer<typeof UnifiedLogSchema>;

/** 标准日志事件结构 (保留兼容旧版) */
export const MonitorEventSchema = z.object({
    category: EventCategorySchema,
    action: z.string(),
    label: z.string().optional(),
    value: z.number().optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
    user_context: z.object({
        user_id: z.string().optional(),
        session_id: z.string().optional(),
        page: z.string(),
    }).optional(),
    timestamp: z.number(),
});

export type MonitorEvent = z.infer<typeof MonitorEventSchema>;

/** 预定义动作常量 */
export const MonitorAction = {
    NAVIGATE: 'navigate',
    CHAT_SEND: 'chat_send',
    KB_CREATE: 'kb_create',
    FILE_UPLOAD: 'file_upload',
    PAGE_LOAD: 'page_load',
    API_CALL: 'api_call',
    ERROR_REPORT: 'error_report'
} as const;
