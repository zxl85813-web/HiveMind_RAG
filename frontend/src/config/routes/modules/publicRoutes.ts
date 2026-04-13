import type { AppRouteMeta } from '../../appRoutes';

export const publicRoutes: AppRouteMeta[] = [
    { key: 'dashboard', path: '/', labelKey: 'nav.dashboard', icon: 'AppstoreOutlined', showInMenu: true, category: 'insight' },
    { key: 'knowledge', path: '/knowledge', labelKey: 'nav.knowledge', icon: 'DatabaseOutlined', showInMenu: true, category: 'cognitive' },
    { key: 'studio', path: '/studio', labelKey: 'nav.studio', icon: 'RocketOutlined', showInMenu: true, category: 'studio' },
    { key: 'agents', path: '/agents', labelKey: 'nav.agents', icon: 'ClusterOutlined', showInMenu: true, category: 'cognitive' },
    { key: 'learning', path: '/learning', labelKey: 'nav.learning', icon: 'BulbOutlined', showInMenu: true, category: 'cognitive' },
    { key: 'login', path: '/login', labelKey: 'Login', icon: 'LockOutlined', showInMenu: false },
];