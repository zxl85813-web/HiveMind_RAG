/**
 * Axios 实例 — 统一 HTTP 请求配置。
 *
 * 所有 API 请求必须通过此实例发出。
 * 禁止在组件中直接使用 fetch/axios。
 *
 * @module services
 * @see .agent/rules/coding-standards.md
 * @see REGISTRY.md > 前端 > Services > api
 */

import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// === Mock Interceptor ===
if (import.meta.env.VITE_USE_MOCK === 'true') {
    console.warn('🛠️ [Frontend] Running in MOCK Mode');
    api.interceptors.request.use(async (config) => {
        const { mockHandlers, sleep } = await import('../mock/handlers');
        const { specialCases } = await import('../mock/specialCases');

        const mockCase = localStorage.getItem('VITE_MOCK_CASE');

        // Handle special cases if requested (Priority over normal mocks)
        if (mockCase && specialCases[mockCase]) {
            const scenario = specialCases[mockCase];
            console.warn(`🧪 [Mock] Special Scenario: ${mockCase}`);
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

        // Extract pure path without query strings
        const pureUrl = config.url?.replace(config.baseURL || '', '').split('?')[0];
        const key = `${config.method?.toUpperCase()}:${pureUrl}`;

        if (mockHandlers[key]) {
            console.log(`🎯 [Mock] Intercepted: ${key}`);
            await sleep(500); // 模拟网络延迟
            config.adapter = async () => ({
                data: mockHandlers[key],
                status: 200,
                statusText: 'OK',
                headers: {},
                config,
            });
        } else {
            // Dynamic route matching for paths like /knowledge/{id}/graph, /knowledge/{id}/documents
            // Match /knowledge/{any-kb-id}/graph -> use kb-001 mock
            if (pureUrl && config.method?.toUpperCase() === 'GET') {
                const graphMatch = pureUrl.match(/^\/knowledge\/[^/]+\/graph$/);
                const docsMatch = pureUrl.match(/^\/knowledge\/[^/]+\/documents$/);
                let fallbackKey: string | undefined;

                if (graphMatch) {
                    fallbackKey = 'GET:/knowledge/kb-001/graph';
                } else if (docsMatch) {
                    fallbackKey = 'GET:/knowledge/kb-001/documents';
                }

                if (fallbackKey && mockHandlers[fallbackKey]) {
                    console.log(`🎯 [Mock] Dynamic match: ${key} -> ${fallbackKey}`);
                    await sleep(500);
                    config.adapter = async () => ({
                        data: mockHandlers[fallbackKey!],
                        status: 200,
                        statusText: 'OK',
                        headers: {},
                        config,
                    });
                }
            }
        }
        return config;
    });
}

// 请求拦截器 — 注入 auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error),
);

// 响应拦截器 — 统一错误处理
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // TODO: 统一错误提示 (通过 antd message)
        // TODO: 401 自动跳转到登录
        console.error('[API Error]', error.response?.status, error.response?.data);
        return Promise.reject(error);
    },
);

export default api;
