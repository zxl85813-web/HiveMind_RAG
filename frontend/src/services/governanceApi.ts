import api from './api';

export interface ProtocolIncident {
    category: 'contract_drift' | 'case_mismatch' | 'type_mismatch' | 'logical_error';
    component: string;
    action: string;
    data_sent: any;
    data_received: any;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    stack_trace?: string;
}

export const governanceApi = {
    reportIncident: (incident: ProtocolIncident) => {
        return api.post('/governance/incidents', incident);
    }
};

/**
 * 🛡️ [FE-GOV-GUARD]: Contract Integrity Guard
 * Used to detect and "force record" mismatches between FE expectations and BE reality.
 */
export class ContractGuard {
    /**
     * Case-insensitive check for status strings
     * @param value The value received from backend
     * @param expected The lowercase value expected by frontend
     * @returns The value (normalized if possible)
     */
    static checkStatus(value: any, expected: string, context: { component: string, action: string, payload?: any }): string {
        if (typeof value !== 'string') return value;

        const normalized = value.toLowerCase();
        
        // The core issue reported by the user: "backend sends success frontend judged Success"
        // If we expect lowercase but get something else (e.g. "Success", "SUCCESS")
        if (value !== expected && normalized === expected.toLowerCase()) {
            console.warn(`[ContractGuard] Detected case drift: got "${value}", expected "${expected}" in ${context.component}`);
            
            // Force Record the Problem
            governanceApi.reportIncident({
                category: 'case_mismatch',
                component: context.component,
                action: context.action,
                data_sent: context.payload || {},
                data_received: { received_value: value, expected_value: expected },
                severity: 'medium',
                stack_trace: new Error().stack
            });

            return normalized;
        }

        return value;
    }

    /**
     * General assertion to find drifting structures
     */
    static assertShape<T>(data: any, validator: (obj: any) => boolean, context: Omit<ProtocolIncident, 'data_received' | 'category'>): T {
        if (!validator(data)) {
            governanceApi.reportIncident({
                ...context,
                category: 'contract_drift',
                data_received: data,
                severity: 'high',
                stack_trace: new Error().stack
            });
        }
        return data as T;
    }
}
