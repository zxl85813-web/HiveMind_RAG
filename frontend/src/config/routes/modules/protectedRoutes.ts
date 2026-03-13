import type { AppRouteMeta } from '../../appRoutes';

export const protectedRoutes: AppRouteMeta[] = [
    { key: 'audit', path: '/audit', labelKey: 'nav.audit', icon: 'SafetyCertificateOutlined', showInMenu: true, access: { anyPermissions: ['audit:review'] } },
    { key: 'security', path: '/security', labelKey: 'nav.security', icon: 'LockOutlined', showInMenu: true, access: { anyPermissions: ['security:manage'] } },
    { key: 'evaluation', path: '/evaluation', labelKey: 'nav.evaluation', icon: 'LineChartOutlined', showInMenu: true, access: { anyPermissions: ['evaluation:run'] } },
    { key: 'finetuning', path: '/finetuning', labelKey: 'nav.finetuning', icon: 'FolderOpenOutlined', showInMenu: true, access: { anyPermissions: ['finetuning:manage'] } },
    { key: 'pipelines', path: '/pipelines', labelKey: 'nav.pipelines', icon: 'SisternodeOutlined', showInMenu: true, access: { anyPermissions: ['pipeline:edit'] } },
    { key: 'canvasLab', path: '/canvas-lab', labelKey: 'nav.canvasLab', icon: 'DeploymentUnitOutlined', showInMenu: true, access: { anyPermissions: ['pipeline:edit'] } },
    { key: 'batch', path: '/batch', labelKey: 'nav.batch', icon: 'ClusterOutlined', showInMenu: true, access: { anyPermissions: ['batch:operate'] } },
    { key: 'settings', path: '/settings', labelKey: 'nav.settings', icon: 'SettingOutlined', showInMenu: true, access: { anyPermissions: ['settings:manage'] } },
];