/**
 * Quick Commands Registry — AI-First 快捷指令注册表。
 *
 * 统一管理所有前端可快速匹配的指令:
 *   - 导航跳转
 *   - 弹窗唤起
 *   - 快捷操作
 *
 * 新增指令只需在此文件添加一行，前端 ChatPanel 和后端 Supervisor 都会自动生效。
 * 指令通过 `module` 字段标记所属模块，运行时根据 PLATFORM_MODE 自动过滤。
 *
 * @module config
 * @see docs/design/ai-first-frontend.md
 */

import type { AIAction } from '../types';

// ============================================================
//  Quick Command 类型定义
// ============================================================

export interface QuickCommand {
    /** 唯一标识符，用于调试和日志 */
    id: string;
    /** 触发关键词列表（大小写不敏感，包含匹配） */
    keywords: string[];
    /** AI 回复文字（支持 Markdown） */
    reply: string;
    /** 附带的交互按钮 */
    actions: AIAction[];
    /** 分类标签，便于管理面板筛选 */
    category: 'navigate' | 'modal' | 'action';
    /** 是否启用 */
    enabled: boolean;
    /** 所属模块: 'core' 始终可用, 'rag' RAG 模式, 'agent' Agent 模式 */
    module: 'core' | 'rag' | 'agent';
}

// ============================================================
//  指令注册表 — 在这里添加新指令
// ============================================================

export const QUICK_COMMANDS: QuickCommand[] = [
    // === 知识库 (RAG) ===
    {
        id: 'create_kb',
        keywords: ['创建知识库', '新建知识库', 'create kb', 'create knowledge base'],
        reply: '好的，为您打开 **创建知识库** 向导 👇',
        actions: [{ type: 'open_modal', target: 'create_kb', label: '立刻创建', variant: 'primary' }],
        category: 'modal',
        enabled: true,
        module: 'rag',
    },
    {
        id: 'nav_knowledge',
        keywords: ['去知识库', '跳转知识库', '打开知识库', 'go to knowledge', '知识库管理'],
        reply: '好的，为您跳转到 **知识库** 👇',
        actions: [{ type: 'navigate', target: '/knowledge', label: '打开知识库', icon: 'DatabaseOutlined', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'rag',
    },
    {
        id: 'upload_doc',
        keywords: ['上传文档', '上传文件', 'upload document', 'upload file'],
        reply: '好的，为您跳转到 **知识库管理** 页面上传文档 👇',
        actions: [{ type: 'navigate', target: '/knowledge', label: '去上传文档', icon: 'UploadOutlined', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'rag',
    },

    // === 评测 (RAG) ===
    {
        id: 'nav_eval',
        keywords: ['去评测', '运行评测', '跳转评测', 'evaluation', '评测中心'],
        reply: '好的，为您跳转到 **评测中心** 👇',
        actions: [{ type: 'navigate', target: '/evaluation', label: '前往评测中心', icon: 'ExperimentOutlined', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'rag',
    },

    // === 安全 (Core) ===
    {
        id: 'nav_security',
        keywords: ['安全中心', '安全审计', 'security', '脱敏'],
        reply: '好的，为您跳转到 **安全中心** 👇',
        actions: [{ type: 'navigate', target: '/security', label: '前往安全中心', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'core',
    },
    {
        id: 'nav_audit',
        keywords: ['审计日志', '操作审计', 'audit log', '查看审计'],
        reply: '好的，为您跳转到 **审计日志** 👇',
        actions: [{ type: 'navigate', target: '/audit', label: '查看审计日志', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'core',
    },

    // === Agent ===
    {
        id: 'nav_agents',
        keywords: ['查看 agent', '查看智能体', 'agent 列表', 'agents', 'agent蜂巢'],
        reply: '好的，为您跳转到 **Agent 蜂巢** 👇',
        actions: [{ type: 'navigate', target: '/agents', label: '查看 Agent', icon: 'ClusterOutlined', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'agent',
    },

    // === 其他页面 ===
    {
        id: 'nav_settings',
        keywords: ['去设置', '打开设置', 'settings', '系统设置'],
        reply: '好的，为您跳转到 **系统设置** 👇',
        actions: [{ type: 'navigate', target: '/settings', label: '打开设置', icon: 'SettingOutlined', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'core',
    },
    {
        id: 'nav_finetuning',
        keywords: ['微调', 'fine-tuning', 'finetuning', '去微调'],
        reply: '好的，为您跳转到 **模型微调** 页面 👇',
        actions: [{ type: 'navigate', target: '/finetuning', label: '前往微调', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'rag',
    },
    {
        id: 'nav_pipelines',
        keywords: ['流水线', 'pipeline', '数据流水线', '去流水线'],
        reply: '好的，为您跳转到 **Pipeline 管理** 👇',
        actions: [{ type: 'navigate', target: '/pipelines', label: '前往 Pipeline', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'rag',
    },
    {
        id: 'nav_studio',
        keywords: ['工作台', 'studio', 'prompt studio', '去工作台'],
        reply: '好的，为您跳转到 **Prompt Studio** 👇',
        actions: [{ type: 'navigate', target: '/studio', label: '打开工作台', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'agent',
    },
    {
        id: 'nav_batch',
        keywords: ['批处理', 'batch', '批量任务', '去批处理'],
        reply: '好的，为您跳转到 **批处理任务** 👇',
        actions: [{ type: 'navigate', target: '/batch', label: '前往批处理', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'agent',
    },
    {
        id: 'nav_learning',
        keywords: ['技术动态', 'learning', '技术学习', '去学习'],
        reply: '好的，为您跳转到 **技术动态** 页面 👇',
        actions: [{ type: 'navigate', target: '/learning', label: '查看动态', icon: 'BulbOutlined', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'rag',
    },
    {
        id: 'nav_dashboard',
        keywords: ['首页', '仪表盘', 'dashboard', '回首页', '去首页'],
        reply: '好的，为您跳转到 **概览** 页面 👇',
        actions: [{ type: 'navigate', target: '/', label: '回到首页', variant: 'primary' }],
        category: 'navigate',
        enabled: true,
        module: 'core',
    },
];

// ============================================================
//  匹配工具函数
// ============================================================

/**
 * 尝试匹配用户输入到快捷指令。
 * 根据平台模式过滤不可用的指令。
 */
export function matchQuickCommand(
    input: string,
    options?: { ragEnabled?: boolean; agentEnabled?: boolean },
): QuickCommand | null {
    const rag = options?.ragEnabled ?? true;
    const agent = options?.agentEnabled ?? true;
    const lower = input.toLowerCase().trim();

    for (const cmd of QUICK_COMMANDS) {
        if (!cmd.enabled) continue;

        // 按平台模式过滤
        if (cmd.module === 'rag' && !rag) continue;
        if (cmd.module === 'agent' && !agent) continue;

        if (cmd.keywords.some(kw => lower.includes(kw.toLowerCase()))) {
            return cmd;
        }
    }
    return null;
}
