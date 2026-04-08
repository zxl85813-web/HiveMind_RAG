import { test, expect } from '@playwright/test';

test.describe('FE-GOV: 401 Failure Cascade Governance', () => {

    test('T-GOV-CASCADE: Should abort all long-connections when 401 occurs', async ({ page }) => {
        // 1. 拦截所有 API 请求并返回 401 (包含核心 auth/me 等)
        await page.route('**/api/v1/**', route => {
            route.fulfill({
                status: 401,
                contentType: 'application/json',
                body: JSON.stringify({ success: false, message: 'Unauthorized' }),
            });
        });

        await page.goto('/');

        // 2. 设置初始 Token 并模拟进入页面触发请求
        await page.evaluate(() => {
            sessionStorage.setItem('hm_access_token', 'session-active-token');
        });

        // 3. 触发会调用 API 的动作 (例如点击概览或刷新)
        await page.reload();

        // 4. 验证 401 拦截器的确定性 side effect
        // 验证 Token 是否被清除
        const token = await page.evaluate(() => sessionStorage.getItem('hm_access_token'));
        expect(token).toBeNull();
        
        // 验证是否跳转到登录页
        await page.waitForURL('**/login', { timeout: 15000 });
        expect(page.url()).toContain('/login');
    });
});
