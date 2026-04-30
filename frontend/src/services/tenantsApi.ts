/**
 * Tenants & usage API — admin tenant ops + per-tenant usage snapshots.
 *
 * @see backend/app/api/routes/tenants.py
 * @see REGISTRY.md > 前端 > Services > tenants
 */

import api from './api';

// ---- Types ----

export interface UsageSnapshot {
    tenant_id: string;
    usage_date: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    request_count: number;
    cost_usd_micro: number;
    quota_tokens_per_day: number | null;
    quota_used_pct: number | null;
    quota_cost_usd_micro_per_day: number | null;
    quota_cost_used_pct: number | null;
    warn_threshold_pct: number | null;
    quota_max_rpm: number | null;
    quota_max_rps: number | null;
    quota_max_tokens_per_user_per_day: number | null;
    quota_max_tokens_per_conversation: number | null;
}

export interface UsageHistoryPoint {
    date: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    request_count: number;
    cost_usd_micro: number;
}

export interface UsageHistory {
    tenant_id: string;
    days: number;
    points: UsageHistoryPoint[];
}

export interface TenantInfo {
    id: string;
    slug: string;
    name: string;
    plan: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

// ---- API calls ----

/** Today's usage for the caller's own tenant. */
export const getMyUsage = () =>
    api.get<UsageSnapshot>('/tenants/_me/usage').then((r) => r.data);

/** Last N days of usage for the caller's own tenant. */
export const getMyUsageHistory = (days = 30) =>
    api
        .get<UsageHistory>('/tenants/_me/usage/history', { params: { days } })
        .then((r) => r.data);

/** Caller's own tenant. */
export const getMyTenant = () =>
    api.get<TenantInfo>('/tenants/_me/current').then((r) => r.data);

/** Force a flush of in-memory accountant counters (admin). */
export const flushUsage = (tenantId: string) =>
    api.post(`/tenants/${tenantId}/usage/flush`).then((r) => r.data);

// ---- Helpers ----

/** Convert micro-USD to a friendly $X.XXXX string. */
export const formatCostMicro = (micro: number): string => {
    const usd = micro / 1_000_000;
    if (usd >= 1) return `$${usd.toFixed(2)}`;
    if (usd >= 0.01) return `$${usd.toFixed(4)}`;
    return `$${usd.toFixed(6)}`;
};
