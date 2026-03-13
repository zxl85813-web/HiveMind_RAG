export type PermissionKey =
    | 'knowledge:manage'
    | 'learning:manage'
    | 'audit:review'
    | 'security:manage'
    | 'evaluation:run'
    | 'finetuning:manage'
    | 'pipeline:edit'
    | 'batch:operate'
    | 'settings:manage';

export interface AccessRequirement {
    anyRoles?: string[];
    anyPermissions?: PermissionKey[];
}

export const ROLE_PERMISSION_MAP = {
    admin: ['knowledge:manage', 'learning:manage', 'audit:review', 'security:manage', 'evaluation:run', 'finetuning:manage', 'pipeline:edit', 'batch:operate', 'settings:manage'],
    operator: ['knowledge:manage', 'learning:manage', 'audit:review', 'evaluation:run', 'finetuning:manage', 'pipeline:edit', 'batch:operate'],
    viewer: [],
} as const;