/**
 * MSW server 实例 — 用于 Vitest 测试环境的 API mock。
 *
 * 生命周期由 setup.ts 管理：
 *   - beforeAll: server.listen({ onUnhandledRequest: 'error' })
 *   - afterEach: server.resetHandlers()
 *   - afterAll: server.close()
 *
 * @validates Requirements 5.2, 5.5
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
