import type { AppRouteMeta } from '../../appRoutes';

export const publicRoutes: AppRouteMeta[] = [
    { key: 'dashboard', path: '/', labelKey: 'nav.dashboard', icon: 'AppstoreOutlined', showInMenu: true },
    { key: 'knowledge', path: '/knowledge', labelKey: 'nav.knowledge', icon: 'DatabaseOutlined', showInMenu: true },
    { key: 'studio', path: '/studio', labelKey: 'nav.studio', icon: 'RocketOutlined', showInMenu: true },
    { key: 'agents', path: '/agents', labelKey: 'nav.agents', icon: 'ClusterOutlined', showInMenu: true },
    { key: 'learning', path: '/learning', labelKey: 'nav.learning', icon: 'BulbOutlined', showInMenu: true },
];