/**
 * TypeScript 类型定义 — 复用 shared/types.ts 中的定义。
 *
 * @module types
 * @see shared/types.ts
 * @see REGISTRY.md > 前端 > Types
 */

// ==========================================
//  Common
// ==========================================

export interface ApiResponse<T = unknown> {
    success: boolean;
    data: T;
    message: string;
    code: number;
}

// ==========================================
//  Chat
// ==========================================

export interface ChatRequest {
    message: string;
    conversation_id?: string;
    knowledge_base_ids?: string[];
    model?: string;
    stream?: boolean;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
    /** AI 操作按钮 — 嵌入在回答中的结构化操作 */
    actions?: AIAction[];
    /** 用户反馈: 1=Like, -1=Dislike, 0=None */
    rating?: number;
    metadata?: {
        model?: string;
        sources?: Source[];
        agent_trace?: AgentTraceStep[];
        /** 当前页面上下文 (AI 回答时所在的页面) */
        context_page?: string;
        /** 发送过程中的状态标签 (雷达、图谱等) */
        statuses?: string[];
        /** P2: Performance & Caching */
        prompt_tokens?: number;
        completion_tokens?: number;
        total_tokens?: number;
        latency_ms?: number;
        is_cached?: boolean;
        trace_data?: string;
    };
}

// ==========================================
//  AI Action 系统 — AI-First 核心
// ==========================================

/** AI 可以在回答中嵌入的操作类型 */
export type AIActionType =
    | 'navigate'       // 导航到页面
    | 'open_modal'     // 打开弹窗 (如创建知识库)
    | 'execute'        // 执行后台操作
    | 'suggest'        // 推荐后续操作
    | 'show_data';     // 内联展示数据

/** AI 操作按钮 */
export interface AIAction {
    type: AIActionType;
    label: string;
    icon?: string;
    /** 跳转目标 (路由路径) 或操作标识符 */
    target: string;
    /** 操作参数 */
    params?: Record<string, unknown>;
    /** 按钮样式: primary 突出, default 普通, link 文字链接 */
    variant?: 'primary' | 'default' | 'link';
}

/** Chat Panel 上下文 — 感知当前页面 */
export interface ChatContext {
    /** 当前页面路由 */
    currentPage: string;
    /** 当前页面标题 */
    pageTitle: string;
    /** 当前页面上可用的 AI 快捷操作 */
    availableActions: AIAction[];
    /** 用户在页面中选中的项目 ID */
    selectedItems?: string[];
}

export interface Conversation {
    id: string;
    title: string;
    messages: ChatMessage[];
    created_at: string;
    updated_at: string;
}

export interface ConversationListItem {
    id: string;
    title: string;
    last_message_preview: string;
    created_at: string;
    updated_at: string;
}

// ==========================================
//  Agent
// ==========================================

export interface AgentTraceStep {
    agent_name: string;
    action: string;
    input: string;
    output: string;
    duration_ms: number;
    timestamp: string;
}

export interface AgentStatus {
    agent_name: string;
    status: 'idle' | 'thinking' | 'executing' | 'reflecting';
    current_task?: string;
}

// ==========================================
//  Knowledge Base
// ==========================================

export interface KnowledgeBase {
    id: string;
    name: string;
    description: string;
    owner_id?: string;
    vector_collection?: string;
    is_public?: boolean;
    version?: number;
    created_at: string;
}

export interface KnowledgeBasePermission {
    id: string;
    kb_id: string;
    user_id?: string;
    role_id?: string;
    department_id?: string;
    can_read: boolean;
    can_write: boolean;
    can_manage: boolean;
    created_at: string;
}

export interface TagCategory {
    id: number;
    name: string;
    description?: string;
    color: string;
    is_system: boolean;
    created_at: string;
}

export interface Tag {
    id: number;
    name: string;
    category_id?: number;
    color?: string;
    category?: TagCategory;
    created_at: string;
}

export interface Document {
    id: string;
    filename: string;
    file_type: string;
    file_size: number;
    storage_path: string;
    status: 'pending' | 'processing' | 'parsed' | 'failed' | 'pending_review';
    security_report?: import('./apiTypes').DesensitizationReportRead;
    tags?: Tag[];
    created_at: string;
    updated_at?: string;
}

export interface KBLink {
    knowledge_base_id: string;
    document_id: string;
    status: 'pending' | 'indexing' | 'indexed' | 'failed' | 'pending_review';
    created_at: string;
}

export interface DocumentReview {
    id: string;
    document_id: string;
    reviewer_id?: string;
    review_type: 'auto' | 'manual';
    status: 'pending' | 'approved' | 'rejected' | 'needs_revision';
    quality_score: number;
    content_length_ok: boolean;
    duplicate_ratio: number;
    garble_ratio: number;
    blank_ratio: number;
    pii_count?: number;
    overlap_score?: number;
    format_integrity_ok?: boolean;
    reviewer_comment?: string;
    created_at: string;
    updated_at: string;
}

export interface Source {
    document_id: string;
    document_name: string;
    chunk_content: string;
    relevance_score: number;
    page_number?: number;
}

// ==========================================
//  WebSocket
// ==========================================

export type ServerEventType =
    | 'agent_status'
    | 'notification'
    | 'suggestion'
    | 'todo_update'
    | 'reflection'
    | 'learning_update'
    | 'task_complete'
    | 'heartbeat';

export interface ServerMessage {
    event: ServerEventType;
    data: Record<string, unknown>;
    timestamp: string;
}

// ==========================================
//  External Learning
// ==========================================

export interface TechDiscovery {
    id: string;
    source: string;
    category: string;
    title: string;
    summary: string;
    url: string;
    relevance_score: number;
    impact_score: number;
    github_stars?: number;
    tags: string[];
    discovered_at: string;
}

// ==========================================
//  Shared TODO
// ==========================================

export type TodoPriority = 'low' | 'medium' | 'high' | 'critical';
export type TodoStatus = 'pending' | 'in_progress' | 'waiting_user' | 'completed' | 'cancelled';

export interface TodoItem {
    id: string;
    title: string;
    description: string;
    priority: TodoPriority;
    status: TodoStatus;
    created_by: string;
    assigned_to: string;
    created_at: string;
    due_at?: string;
}
// ==========================================
//  RAG Evaluation (M2.1E)
// ==========================================

export interface EvaluationSet {
    id: string;
    kb_id: string;
    name: string;
    description?: string;
    created_at: string;
}

export interface EvaluationItem {
    id: string;
    set_id: string;
    question: string;
    ground_truth: string;
    reference_context?: string;
}

export interface EvaluationReport {
    id: string;
    set_id: string;
    kb_id: string;

    // M2.5 Multi-model metrics
    model_name: string;
    latency_ms: number;
    cost: number;
    token_usage: number;

    faithfulness: number;
    answer_relevance: number;
    context_precision: number;
    context_recall: number;
    total_score: number;
    details_json: string; // JSON string in backend
    status: 'pending' | 'running' | 'completed' | 'failed';
    created_at: string;
}
export interface FineTuningItem {
    id: string;
    kb_id?: string;
    instruction: string;
    input_context?: string;
    output: string;
    source_type: string;
    source_id?: string;
    status: string;
    created_at: string;
}

// ==========================================
//  Security & Desensitization (M2.2)
// ==========================================

export interface DesensitizationPolicy {
    id: number;
    name: string;
    description?: string;
    is_active: boolean;
    rules_json: string;
    created_at: string;
    updated_at: string;
}

export interface SensitiveItem {
    id: number;
    report_id: string;
    detector_type: string;
    original_text_preview: string;
    redacted_text: string;
    start_index: number;
    end_index: number;
    action_taken: string;
}

export interface DesensitizationReport {
    id: string;
    document_id: string;
    total_items_found: number;
    total_items_redacted: number;
    status: string;
    created_at: string;
    items?: SensitiveItem[];
}
