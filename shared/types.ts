/**
 * Shared protocol definitions between frontend and backend.
 * These TypeScript types mirror the backend Pydantic schemas.
 */

// ==========================================
//  WebSocket Message Protocol
// ==========================================

/** Server → Client event types */
export type ServerEventType =
    | 'agent_status'
    | 'notification'
    | 'suggestion'
    | 'todo_update'
    | 'reflection'
    | 'learning_update'
    | 'task_complete'
    | 'heartbeat';

/** Client → Server event types */
export type ClientEventType =
    | 'cancel'
    | 'ping'
    | 'subscribe'
    | 'unsubscribe';

export interface ServerMessage {
    event: ServerEventType;
    data: Record<string, unknown>;
    timestamp: string;
}

export interface ClientMessage {
    event: ClientEventType;
    data?: Record<string, unknown>;
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
    metadata?: {
        model?: string;
        sources?: Source[];
        agent_trace?: AgentTraceStep[];
    };
}

export interface Conversation {
    id: string;
    title: string;
    messages: ChatMessage[];
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
    document_count: number;
    created_at: string;
}

export interface Source {
    document_id: string;
    document_name: string;
    chunk_content: string;
    relevance_score: number;
    page_number?: number;
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

export interface Subscription {
    id: string;
    topic: string;
    sources: string[];
    min_relevance: number;
    is_active: boolean;
}

// ==========================================
//  Batch Processing
// ==========================================

export type TaskStatus = 'pending' | 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'retry_wait';
export type BatchStatus = 'created' | 'running' | 'completed' | 'partial' | 'failed' | 'cancelled';

export interface TaskStep {
    name: string;
    agent_name?: string;
    prompt_template: string;
    config: Record<string, unknown>;
}

export interface TaskUnit {
    id: string;
    batch_job_id: string;
    name: string;
    input_data: Record<string, unknown>;
    steps: TaskStep[];
    depends_on: string[];
    priority: number;
    status: TaskStatus;
    retry_count: number;
    max_retries: number;
    output_data: Record<string, unknown>;
    error_message: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    worker_id: string;
}

export interface BatchJob {
    id: string;
    name: string;
    description: string;
    tasks: Record<string, TaskUnit>;
    total_tasks: number;
    status: BatchStatus;
    max_concurrency: number;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    progress: Record<string, number>;
    completion_rate: number;
    success_rate: number;
}
