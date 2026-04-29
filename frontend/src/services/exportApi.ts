/**
 * Export API client — drives the blueprint export wizard.
 *
 * Endpoints mirror backend/app/api/routes/export.py.
 */

import api from './api';

export type PlatformMode = 'rag' | 'agent' | 'full';
export type UIMode = 'full' | 'single_agent' | 'widget';
export type LLMProvider = 'openai' | 'ark' | 'local_vllm' | 'ollama' | 'other';

export interface AssetEntry {
    id: string;
    kind: 'skill' | 'mcp_server' | 'agent_template';
    path: string;
    description?: string;
}

export interface AssetCatalog {
    skills: AssetEntry[];
    mcp_servers: AssetEntry[];
    agent_templates: AssetEntry[];
}

export interface AgentSpec {
    id: string;
    name: string;
    system_prompt?: string;
    skills: string[];
    mcp_servers: string[];
}

export interface BlueprintDraft {
    name: string;
    version: string;
    customer: string;
    description?: string;
    platform_mode: PlatformMode;
    ui_mode: UIMode;
    llm: {
        provider: LLMProvider;
        model: string;
        base_url?: string;
    };
    agents: AgentSpec[];
    default_agent_id?: string | null;
    knowledge_bases: string[];
    extra_paths: string[];
    env_overrides: Record<string, string | boolean | null>;
}

export interface ValidationFieldError {
    loc: (string | number)[];
    msg: string;
    type: string;
}

export interface ValidationResponse {
    success: boolean;
    message?: string;
    errors?: ValidationFieldError[];
    /** Present when success === true */
    data?: {
        name: string;
        version: string;
        platform_mode: PlatformMode;
        ui_mode: UIMode;
        default_agent_id: string | null;
    };
}

export interface ExportJobEvent {
    ts: number;
    step: string;
    status: 'start' | 'ok' | 'skip' | 'warn' | 'error';
    detail?: string;
}

export interface ExportJob {
    id: string;
    blueprint_name: string;
    status: 'pending' | 'running' | 'succeeded' | 'failed';
    output_dir?: string | null;
    zip_path?: string | null;
    files_written: number;
    bytes_written: number;
    warnings: string[];
    error?: string | null;
    created_at: number;
    finished_at?: number | null;
    events: ExportJobEvent[];
}

interface ApiEnvelope<T> {
    success: boolean;
    data: T;
    message: string;
}

export const exportApi = {
    async listAssets(): Promise<AssetCatalog> {
        const { data } = await api.get<ApiEnvelope<AssetCatalog>>('/export/assets');
        return data.data;
    },

    async validate(blueprint: BlueprintDraft): Promise<ValidationResponse> {
        const { data } = await api.post<ValidationResponse | ApiEnvelope<unknown>>(
            '/export/blueprints/validate',
            { blueprint }
        );
        // Endpoint returns either ApiResponse.ok({...}) on success or
        // a ValidationErrorResponse on schema failure — both share `success`.
        return data as ValidationResponse;
    },

    async submit(blueprint: BlueprintDraft, makeZip = true): Promise<ExportJob> {
        const { data } = await api.post<ApiEnvelope<ExportJob>>('/export/jobs', {
            blueprint,
            make_zip: makeZip,
        });
        return data.data;
    },

    async getJob(jobId: string): Promise<ExportJob> {
        const { data } = await api.get<ApiEnvelope<ExportJob>>(`/export/jobs/${jobId}`);
        return data.data;
    },

    async listJobs(): Promise<ExportJob[]> {
        const { data } = await api.get<ApiEnvelope<ExportJob[]>>('/export/jobs');
        return data.data;
    },

    /** Returns the absolute URL the wizard can open in a new tab. */
    downloadUrl(jobId: string): string {
        const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api/v1';
        return `${base}/export/jobs/${jobId}/download`;
    },

    /** SSE endpoint for real-time progress; consumed by EventSource. */
    streamUrl(jobId: string): string {
        const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api/v1';
        return `${base}/export/jobs/${jobId}/stream`;
    },

    async deleteJob(jobId: string): Promise<void> {
        await api.delete(`/export/jobs/${jobId}`);
    },
};
