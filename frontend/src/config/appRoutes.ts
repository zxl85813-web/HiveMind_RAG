import type { AccessRequirement } from './access';
import { publicRoutes } from './routes/modules/publicRoutes';
import { protectedRoutes } from './routes/modules/protectedRoutes';

export interface AppRouteMeta {
    key: string;
    path: string;
    labelKey: string;
    icon: string;
    showInMenu: boolean;
    category?: 'insight' | 'cognitive' | 'studio' | 'lab' | 'observability' | 'sovereign' | 'system';
    access?: AccessRequirement;
}

export const appRoutes: AppRouteMeta[] = [...publicRoutes, ...protectedRoutes];