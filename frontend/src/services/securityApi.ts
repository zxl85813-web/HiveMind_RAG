import api from './api';
import type { ApiResponse, DesensitizationPolicy, DesensitizationReport } from '../types';
import type {
    AuditLogRead,
    DocumentPermissionCreate,
    DocumentPermissionRead,
} from '../types/apiTypes';

export interface CreatePolicyParams {
    name: string;
    description?: string;
    is_active?: boolean;
    rules_json: string;
}

export interface AvailableDetector {
    name: string;
    description?: string;
    [key: string]: unknown;
}

export const securityApi = {
    // 获取脱敏策略列表
    listPolicies: () =>
        api.get<ApiResponse<DesensitizationPolicy[]>>('/security/policies'),

    // 创建策略
    createPolicy: (data: CreatePolicyParams) =>
        api.post<ApiResponse<DesensitizationPolicy>>('/security/policies', data),

    // 激活指定策略
    activatePolicy: (id: number) =>
        api.put<ApiResponse<DesensitizationPolicy>>(`/security/policies/${id}/activate`),

    // 获取文档脱敏报告
    getReport: (documentId: string) =>
        api.get<ApiResponse<DesensitizationReport>>(`/security/reports/document/${documentId}`),

    // 获取系统可用的检测器列表
    getDetectors: () =>
        api.get<ApiResponse<{ available_detectors: AvailableDetector[] }>>('/security/detectors'),

    // --- ACL & Governance (P1) ---
    getDocumentPermissions: (documentId: string) =>
        api.get<ApiResponse<DocumentPermissionRead[]>>(`/security/permissions/document/${documentId}`),

    grantPermission: (data: DocumentPermissionCreate) =>
        api.post<ApiResponse<DocumentPermissionRead>>('/security/permissions', data),

    revokePermission: (id: string) =>
        api.delete<ApiResponse<{ status: string }>>(`/security/permissions/${id}`),

    listAuditLogs: (limit: number = 50) =>
        api.get<ApiResponse<AuditLogRead[]>>(`/security/audit/logs?limit=${limit}`),
};
