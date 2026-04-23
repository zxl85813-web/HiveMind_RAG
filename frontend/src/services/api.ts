/**
 * Axios 实例 — 统一 HTTP 请求配置。
 */

import axios from 'axios';
// import { notification } from 'antd'; // Removed static import
import { AppError } from '../core/AppError';
import { monitor } from '../core/MonitorService';
import { ErrorCode } from '../core/schema/error';
import i18n from '../i18n/config';
import { tokenVault } from '../core/auth/TokenVault';
import { connectionManager } from '../core/ConnectionManager';
import antdStatic from '../core/antdStatic';
 
declare global {
  interface Window {
    isAuthRedirecting?: boolean;
  }
}

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// === Mock Interceptor ===
if (import.meta.env.VITE_USE_MOCK === 'true') {
    api.interceptors.request.use(async (config) => {
        const { mockHandlers, sleep } = await import('../mock/handlers');
        const { specialCases } = await import('../mock/specialCases');
        const mockCase = localStorage.getItem('VITE_MOCK_CASE');

        if (mockCase && specialCases[mockCase]) {
            const scenario = specialCases[mockCase];
            await sleep(scenario.delay || 500);
            config.adapter = async () => ({
                data: scenario.data,
                status: scenario.status || 200,
                statusText: scenario.status === 200 ? 'OK' : 'Error',
                headers: {},
                config,
            });
            return config;
        }

        // 🛰️ [FE-GOV-FIX]: 增强 URL 剥离逻辑，支持绝对路径与相对路径的 Mock 命中
        let pureUrl = config.url || '';
        if (pureUrl.startsWith('http')) {
            try {
                pureUrl = new URL(pureUrl).pathname.replace(config.baseURL || '', '');
            } catch {
                pureUrl = pureUrl.replace(config.baseURL || '', '');
            }
        } else {
            pureUrl = pureUrl.replace(config.baseURL || '', '');
        }
        pureUrl = pureUrl.split('?')[0];
        
        const key = `${config.method?.toUpperCase()}:${pureUrl}`;

        if (mockHandlers[key]) {
            await sleep(500);
            config.adapter = async () => ({
                data: mockHandlers[key],
                status: 200,
                statusText: 'OK',
                headers: {},
                config,
            });
        }
        return config;
    });
}

// 请求拦截器
api.interceptors.request.use(
    (config) => {
        const token = tokenVault.getAccessToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        } else {
            // 🛡️ [Auth-Audit]: 如果是非公开接口但缺少 Token，记录警告
            const isPublicTask = config.url?.includes('/auth/login') || config.url?.includes('/health');
            if (!isPublicTask) {
                console.warn(`[API] Missing token for protected route: ${config.url}`);
            }
        }
        // 🛰️ [FE-GOV-003]: 将前端语言偏好同步至后端
        config.headers['Accept-Language'] = i18n.language || 'zh-CN';
        // 🛰️ [FE-GOV-002]: 全链路追踪同步
        config.headers['X-Trace-Id'] = monitor.getTraceId();
        return config;
    },
    (error) => Promise.reject(error),
);

// 响应拦截器
api.interceptors.response.use(
    (response) => response,
    (error) => {
        const { response } = error;
        const status = (response?.status as number) || 0;
        const msg = String(response?.data?.message || response?.data?.detail || '网络请求异常，请稍后再试');

        let errorCode: string = ErrorCode.API_NETWORK_ERROR;

        if (status === 401) {
            // 🛡️ [Loop-Harden]: 增加单次 401 处理锁，防止并发请求失败导致的重定向死循环
            if (window.isAuthRedirecting) return Promise.reject(error);
            
            if (import.meta.env.VITE_USE_MOCK !== 'true') {
                window.isAuthRedirecting = true;
                tokenVault.clear();
                connectionManager.abortAll();
                
                if (window.location.pathname === '/login') {
                    console.error('[API Error] 401 Unauthorized captured on login page. Suppression active.');
                    window.isAuthRedirecting = false;
                    return Promise.reject(error);
                }

                antdStatic.notification?.warning({
                    title: '登录已过期',
                    description: '您的身份凭证已失效，请重新登录。',
                    placement: 'topRight',
                });
                
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
            } else {
                console.warn('[Mock Warning] Detected 401 error, but suppression is active to prevent redirect loops.');
            }
        }
 else if (status === 403) {
            errorCode = ErrorCode.API_FORBIDDEN;
            antdStatic.notification?.error({
                title: '权限不足',
                description: msg,
            });
        } else if (status >= 500) {
            errorCode = ErrorCode.UNKNOWN_ERROR;
            antdStatic.notification?.error({
                title: '服务器错误',
                description: msg || `后端服务响应异常 (${status})，请稍后重试。`,
            });
        } else if (!response) {
            antdStatic.notification?.error({
                title: '连接失败',
                description: '无法连接到远程服务器，请检查您的网络设置。',
            });
        }

        const appError = new AppError({
            code: errorCode,
            message: msg,
            layer: 'api',
            severity: status >= 500 ? 'high' : 'medium',
            metadata: {
                url: response?.config?.url,
                method: response?.config?.method,
                status,
                requestId: response?.headers?.['x-request-id']
            }
        });

        // 统一上报
        monitor.reportError(appError);

        console.error('[API Error]', status, response?.data);
        return Promise.reject(appError);
    },
);

export default api;
