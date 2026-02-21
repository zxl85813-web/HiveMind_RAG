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
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

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
