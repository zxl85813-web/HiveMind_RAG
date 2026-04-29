/**
 * Vitest 全局 setup — jest-dom matchers 注册 + MSW server 生命周期。
 *
 * 由 vitest.config.ts 的 setupFiles 引用。
 *
 * @see design.md > 前端测试工具接口
 * @validates Requirements 5.1, 5.2
 */

import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './mocks/server';

// MSW server 生命周期管理
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
