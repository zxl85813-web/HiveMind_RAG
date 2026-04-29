import type { AxiosResponse } from 'axios';
import api from './api';

export interface ApiResponse<T> {
    success: boolean;
    data: T;
    message: string;
}

export type TaskStatus = 'pending' | 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'retry_wait';

export interface TaskStep {
    name: string;
    agent_name?: string;
    prompt_template?: string;
    config?: Record<string, any>;
}

export interface TaskUnit {
    id: string;
    batch_job_id: string;
    name: string;
    input_data: Record<string, any>;
    steps: TaskStep[];
    depends_on: string[];
    priority: number;
    status: TaskStatus;
    output_data: Record<string, any>;
    error_message: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    worker_id: string;
    duration_seconds?: number;
    is_terminal: boolean;
}

export type BatchStatus = 'created' | 'running' | 'completed' | 'partial' | 'failed' | 'cancelled';

export interface BatchJob {
    id: string;
    name: string;
    description: string;
    tasks: Record<string, TaskUnit>;
    total_tasks: number;
    status: BatchStatus;
    max_concurrency: number;
    timeout_per_task: number;
    on_failure: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    progress: Record<string, number>;
    completion_rate: number;
    success_rate: number;
}

export interface CreateBatchJobRequest {
    name: string;
    description?: string;
    tasks: any[];
    max_concurrency?: number;
}

export const batchApi = {
    /**
     * Create string and start a new batch job
     */
    createJob: (payload: CreateBatchJobRequest): Promise<AxiosResponse<BatchJob>> => {
        return api.post('/agents/batch/jobs', payload);
    },

    /**
     * Get all jobs
     */
    getJobs: (): Promise<AxiosResponse<BatchJob[]>> => {
        return api.get<BatchJob[]>('/agents/batch/jobs');
    },

    /**
     * Get specific job by ID
     */
    getJob: (id: string): Promise<AxiosResponse<BatchJob>> => {
        return api.get<BatchJob>(`/agents/batch/jobs/${id}`);
    },

    /**
     * Cancel running job
     */
    cancelJob: (id: string): Promise<AxiosResponse<{ status: string }>> => {
        return api.post(`/agents/batch/jobs/${id}/cancel`);
    }
};
