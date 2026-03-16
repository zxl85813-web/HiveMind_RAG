import { useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { monitor } from '../core/MonitorService';
import type { EventCategory } from '../core/schema/monitoring';

/**
 * 🛰️ [FE-GOV-002]: UI 组件级监控 Hook
 */
export function useMonitor() {
    const location = useLocation();

    const track = useCallback((category: EventCategory, action: string, metadata?: Record<string, unknown>) => {
        monitor.log({
            category,
            action,
            metadata,
            user_context: {
                page: location.pathname,
            }
        });
    }, [location.pathname]);

    const report = useCallback((error: Error, metadata?: Record<string, unknown>) => {
        monitor.reportError(error, {
            page: location.pathname,
            ...metadata
        });
    }, [location.pathname]);

    return { track, report };
}
