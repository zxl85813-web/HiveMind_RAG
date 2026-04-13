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
    admin: [
        'knowledge:manage',
        'learning:manage',
        'audit:review',
        'security:manage',
        'evaluation:run',
        'finetuning:manage',
        'pipeline:edit',
        'batch:operate',
        'settings:manage'
    ],
    user: [
        'knowledge:manage',
        'learning:manage',
        'evaluation:run',
        'batch:operate'
    ],
    readonly: [],
} as const;