import { z } from 'zod';

/**
 * 🛰️ [FE-GOV-002]: Schema-Driven 监控体系
 * 
 * 定义系统中用户行为日志与性能指标的结构
 */

export const EventCategorySchema = z.enum(['user_action', 'performance', 'error', 'system']);
export type EventCategory = z.infer<typeof EventCategorySchema>;

/** 标准日志事件结构 */
export const MonitorEventSchema = z.object({
    category: EventCategorySchema,
    action: z.string(), // 操作名称，如 'click_create_kb'
    label: z.string().optional(), // 标签，如 'knowledge_page'
    value: z.number().optional(), // 数值，如 延迟时间或成功率
    metadata: z.record(z.string(), z.unknown()).optional(), // 上下文数据
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
} as const;
