import { test, expect } from '@playwright/test';

test.describe('Persistent Chat Panel', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('should allow interacting with AI Assistant from any page', async ({ page }) => {
        const chatInput = page.locator('textarea[placeholder*="输入你的问题"]');
        await expect(chatInput).toBeVisible();

        // Use standard Sender/Bubble interaction
        await chatInput.fill('你好，HiveMind');
        await page.keyboard.press('Enter');

        // Wait for bubble to appear
        await expect(page.locator('.ant-bubble-content')).toContainText('你好');

        // Navigate away and verify chat persists
        await page.click('text=设置');
        await expect(page.locator('.ant-bubble-content')).toContainText('你好');
    });
});
