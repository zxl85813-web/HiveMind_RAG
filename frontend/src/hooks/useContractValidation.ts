import { useCallback } from 'react';
import { ContractGuard } from '../services/governanceApi';

interface ValidationContext {
    component: string;
    action: string;
}

/**
 * 🎣 [FE-GOV-HOOK]: 强制规约校验 Hook
 * 
 * 当遇到前后端不一致（如 Case 敏感问题）时，不仅会静默修复，还会强制向后端汇报事故并记录。
 */
export function useContractValidation(context: ValidationContext) {
    /**
     * 校验并修复状态字段
     * 示例: validateStatus(res.status, 'success')
     */
    const validateStatus = useCallback((value: any, expected: string, payload?: any) => {
        return ContractGuard.checkStatus(value, expected, {
            ...context,
            payload
        });
    }, [context]);

    /**
     * 手动报告一个遇到的奇葩逻辑或数据结构问题
     */
    const reportManualIncident = useCallback((category: any, message: string, receivedData: any) => {
        const { governanceApi } = require('../services/governanceApi'); // Lazy load to avoid circular deps
        governanceApi.reportIncident({
            category,
            component: context.component,
            action: context.action,
            data_sent: { message },
            data_received: receivedData,
            severity: 'medium',
            stack_trace: new Error().stack
        });
    }, [context]);

    return {
        validateStatus,
        reportManualIncident
    };
}
