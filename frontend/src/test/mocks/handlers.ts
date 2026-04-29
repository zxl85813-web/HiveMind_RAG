/**
 * MSW v2 request handlers — 复用 src/mock/handlers.ts 中的 mock 数据。
 *
 * 将项目已有的 mockHandlers (Record<string, any> 格式) 转换为
 * MSW v2 的 http.get / http.post handler 格式。
 *
 * @validates Requirements 5.2
 */

import { http, HttpResponse } from 'msw';
import { mockHandlers } from '../../mock/handlers';

const API_BASE = '/api/v1';

/**
 * 将 mockHandlers 的 "METHOD:/path" 格式转换为 MSW v2 handler 数组。
 *
 * mockHandlers 的 key 格式: "GET:/knowledge", "POST:/knowledge" 等
 * 转换为: http.get(`${API_BASE}/knowledge`, ...) 等
 */
function buildHandlersFromMockMap() {
  const methodMap: Record<string, typeof http.get> = {
    GET: http.get,
    POST: http.post,
    PUT: http.put,
    PATCH: http.patch,
    DELETE: http.delete,
  };

  return Object.entries(mockHandlers).map(([key, responseData]) => {
    const colonIndex = key.indexOf(':');
    const method = key.slice(0, colonIndex).toUpperCase();
    const path = key.slice(colonIndex + 1);

    const handler = methodMap[method];
    if (!handler) {
      console.warn(`[MSW] Unsupported method "${method}" for key "${key}"`);
      return null;
    }

    return handler(`${API_BASE}${path}`, () => {
      return HttpResponse.json(responseData);
    });
  }).filter(Boolean);
}

/**
 * 导出的 handlers 数组，供 server.ts 使用。
 *
 * 测试中可通过 server.use(...) 覆盖特定 handler 来模拟错误场景。
 */
export const handlers = [
  ...buildHandlersFromMockMap(),

  // 动态路由: /knowledge/:kbId/graph
  http.get(`${API_BASE}/knowledge/:kbId/graph`, () => {
    const fallback = mockHandlers['GET:/knowledge/kb-001/graph'];
    return HttpResponse.json(fallback);
  }),

  // 动态路由: /knowledge/:kbId/documents
  http.get(`${API_BASE}/knowledge/:kbId/documents`, () => {
    const fallback = mockHandlers['GET:/knowledge/kb-001/documents'];
    return HttpResponse.json(fallback);
  }),

  // 动态路由: /agents/batch/jobs/:jobId
  http.get(`${API_BASE}/agents/batch/jobs/:jobId`, ({ params }) => {
    const { jobId } = params;
    const key = `GET:/agents/batch/jobs/${jobId}`;
    const data = mockHandlers[key] || mockHandlers['GET:/agents/batch/jobs/job-001'];
    return HttpResponse.json(data);
  }),

  // 动态路由: /security/permissions/document/:docId
  http.get(`${API_BASE}/security/permissions/document/:docId`, () => {
    const fallback = mockHandlers['GET:/security/permissions/document/doc-001'];
    return HttpResponse.json(fallback);
  }),

  // 动态路由: /audit/:reviewId/approve
  http.post(`${API_BASE}/audit/:reviewId/approve`, () => {
    const fallback = mockHandlers['POST:/audit/rev-1/approve'];
    return HttpResponse.json(fallback);
  }),

  // 动态路由: /audit/:reviewId/reject
  http.post(`${API_BASE}/audit/:reviewId/reject`, () => {
    const fallback = mockHandlers['POST:/audit/rev-1/reject'];
    return HttpResponse.json(fallback);
  }),

  // 动态路由: /evaluation/:setId/evaluate
  http.post(`${API_BASE}/evaluation/:setId/evaluate`, () => {
    const fallback = mockHandlers['POST:/evaluation/set-finance/evaluate'];
    return HttpResponse.json(fallback);
  }),
] as ReturnType<typeof http.get>[];
