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
import { notification } from 'antd';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 🔒 [Architecture-Gate]: 全局网关与错误拦截
// 职责: 统一处理 HTTP 异常，特别是身份过期 (401) 和服务端崩溃 (5xx)。
// 设计决策: 使用 antd static notification 确保非 React 环境下也能触发 UI 反馈。

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

            // DELETE /agents/mcp/servers/{name} → return synthetic success (mock-only)
            if (pureUrl && config.method?.toUpperCase() === 'DELETE'
                && /^\/agents\/mcp\/servers\/[^/]+$/.test(pureUrl)) {
                const name = decodeURIComponent(pureUrl.split('/').pop() || '');
                console.log(`🎯 [Mock] Dynamic DELETE: ${key}`);
                await sleep(400);
                config.adapter = async () => ({
                    data: { success: true, data: { name, deleted: true }, message: 'Deleted (mock)' },
                    status: 200,
                    statusText: 'OK',
                    headers: {},
                    config,
                });
            }

            // DELETE /agents/swarm/agents/{name} → return synthetic success (mock-only)
            if (pureUrl && config.method?.toUpperCase() === 'DELETE'
                && /^\/agents\/swarm\/agents\/[^/]+$/.test(pureUrl)) {
                const name = decodeURIComponent(pureUrl.split('/').pop() || '');
                console.log(`🎯 [Mock] Dynamic DELETE agent: ${key}`);
                await sleep(300);
                config.adapter = async () => ({
                    data: { success: true, data: { name, deleted: true }, message: 'Deleted (mock)' },
                    status: 200,
                    statusText: 'OK',
                    headers: {},
                    config,
                });
            }

            // DELETE /agents/skills/{name} → mock uninstall
            if (pureUrl && config.method?.toUpperCase() === 'DELETE'
                && /^\/agents\/skills\/[^/]+$/.test(pureUrl)) {
                const name = decodeURIComponent(pureUrl.split('/').pop() || '');
                console.log(`🎯 [Mock] Dynamic DELETE skill: ${key}`);
                await sleep(300);
                config.adapter = async () => ({
                    data: { success: true, data: { name, deleted: true, files_removed: true }, message: 'Skill uninstalled (mock)' },
                    status: 200,
                    statusText: 'OK',
                    headers: {},
                    config,
                });
            }

            // POST /agents/skills/{name}/toggle → mock enable/disable
            if (pureUrl && config.method?.toUpperCase() === 'POST'
                && /^\/agents\/skills\/[^/]+\/toggle/.test(pureUrl)) {
                const path = pureUrl.split('?')[0];
                const name = decodeURIComponent(path.split('/').slice(-2)[0] || '');
                const enabled = /enabled=true/i.test(pureUrl);
                console.log(`🎯 [Mock] Dynamic POST toggle skill: ${key}`);
                await sleep(200);
                config.adapter = async () => ({
                    data: { success: true, data: { name, enabled }, message: 'Skill toggled (mock)' },
                    status: 200,
                    statusText: 'OK',
                    headers: {},
                    config,
                });
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
        const { response } = error;
        const status = response?.status;
        const msg = response?.data?.message || response?.data?.detail || '网络请求异常，请稍后再试';

        if (status === 401) {
            // 令牌过期或未登录
            notification.warning({
                message: '登录已过期',
                description: '您的身份凭证已失效，请重新登录。',
                placement: 'topRight',
            });
            localStorage.removeItem('access_token');
            // 延迟跳转，给用户看一眼通知的时间
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
        } else if (status === 403) {
            notification.error({
                message: '权限不足',
                description: msg || '您没有权限执行此操作。',
            });
        } else if (status >= 500) {
            notification.error({
                message: '服务器错误',
                description: msg || `后端服务响应异常 (${status})，请稍后重试。`,
            });
        } else if (!response) {
            notification.error({
                message: '连接失败',
                description: '无法连接到远程服务器，请检查您的网络设置。',
            });
        }

        console.error('[API Error]', status, response?.data);
        return Promise.reject(error);
    },
);

export default api;
