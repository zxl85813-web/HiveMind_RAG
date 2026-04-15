import type { AppRouteMeta } from '../../appRoutes';

export const protectedRoutes: AppRouteMeta[] = [
    { key: 'audit', path: '/audit', labelKey: 'nav.audit', icon: 'SafetyCertificateOutlined', showInMenu: true, category: 'observability', access: { anyPermissions: ['audit:review'] } },
    { key: 'devGovernance', path: '/governance/dev', labelKey: 'nav.devGovernance', icon: 'SafetyCertificateOutlined', showInMenu: true, category: 'sovereign' },
    { key: 'agentGovernance', path: '/governance/agent', labelKey: 'nav.agentGovernance', icon: 'BulbOutlined', showInMenu: true, category: 'sovereign' },
    { key: 'architectureAssets', path: '/governance/assets', labelKey: 'nav.architectureAssets', icon: 'DatabaseOutlined', showInMenu: false, category: 'sovereign' },
    { key: 'security', path: '/security', labelKey: 'nav.security', icon: 'LockOutlined', showInMenu: true, category: 'sovereign', access: { anyPermissions: ['security:manage'] } },
    { key: 'evaluation', path: '/evaluation', labelKey: 'nav.evaluation', icon: 'LineChartOutlined', showInMenu: true, category: 'lab', access: { anyPermissions: ['evaluation:run'] } },
    { key: 'finetuning', path: '/finetuning', labelKey: 'nav.finetuning', icon: 'FolderOpenOutlined', showInMenu: true, category: 'lab', access: { anyPermissions: ['finetuning:manage'] } },
    { key: 'pipelines', path: '/pipelines', labelKey: 'nav.pipelines', icon: 'SisternodeOutlined', showInMenu: true, category: 'studio', access: { anyPermissions: ['pipeline:edit'] } },
    { key: 'canvasLab', path: '/canvas-lab', labelKey: 'nav.canvasLab', icon: 'DeploymentUnitOutlined', showInMenu: true, category: 'studio', access: { anyPermissions: ['pipeline:edit'] } },
    { key: 'batch', path: '/batch', labelKey: 'nav.batch', icon: 'ClusterOutlined', showInMenu: true, category: 'lab', access: { anyPermissions: ['batch:operate'] } },
    { key: 'settings', path: '/settings', labelKey: 'nav.settings', icon: 'SettingOutlined', showInMenu: true, category: 'system', access: { anyPermissions: ['settings:manage'] } },
    { key: 'architectureLab', path: '/architecture-lab', labelKey: 'nav.architectureLab', icon: 'ExperimentOutlined', showInMenu: true, category: 'system', access: { anyPermissions: ['settings:manage'] } },
    { key: 'tokenDashboard', path: '/token-dashboard', labelKey: 'nav.tokenDashboard', icon: 'DashboardOutlined', showInMenu: true, category: 'observability', access: { anyPermissions: ['settings:manage'] } },
    { key: 'kbAnalytics', path: '/kb-analytics', labelKey: 'nav.kbAnalytics', icon: 'AreaChartOutlined', showInMenu: true, category: 'lab', access: { anyPermissions: ['settings:manage'] } },
    { key: 'trace', path: '/trace', labelKey: 'nav.trace', icon: 'NodeIndexOutlined', showInMenu: true, category: 'observability', access: { anyPermissions: ['settings:manage'] } },
];