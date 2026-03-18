import { test, expect } from '@playwright/test';

test.describe('HiveMind Governance Suite', () => {
    test.beforeEach(async ({ page }) => {
        // 强制初始化为中文环境
        await page.addInitScript(() => {
            window.localStorage.setItem('i18nextLng', 'zh-CN');
            window.localStorage.removeItem('VITE_MOCK_CASE');
        });
        await page.goto('/');
    });

    test('PWA Metadata Verification', async ({ page }) => {
        await expect(page).toHaveTitle(/HiveMind RAG/);
        const themeColor = await page.locator('meta[name="theme-color"]').getAttribute('content');
        expect(themeColor).toBe('#317EFB');
        const appleIcon = await page.locator('link[rel="apple-touch-icon"]').getAttribute('href');
        expect(appleIcon).toBe('/icon-512.png');
    });

    test('i18n Language Persistence', async ({ page }) => {
        // 验证默认中文
        await expect(page.getByText('概览')).toBeVisible();

        // 切换到英语
        await page.evaluate(() => {
            localStorage.setItem('i18nextLng', 'en-US');
        });
        await page.reload();

        // 验证英文 UI
        await expect(page.getByText('Dashboard')).toBeVisible();
    });

    test('Dynamic Component Loading (Lazy)', async ({ page }) => {
        // 点击进入画布实验室 (G6/X6 懒加载)
        await page.click('text=画布实验室');
        
        // 检查渲染容器
        await expect(page.locator('.ant-tabs-content-holder')).toBeVisible();
        
        // 验证至少有一个 Canvas 渲染出来 (代表 AntV 库已成功加载)
        await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });
    });
});
