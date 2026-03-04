import { test, expect } from '@playwright/test';

test.describe('Learning & Discovery Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/learning');
    });

    test('should show tech discoveries list', async ({ page }) => {
        await expect(page.getByText('技术动态')).toBeVisible();
        const cards = page.locator('.ant-card-hoverable');
        await expect(cards).toHaveCount(20); // From mockData
    });

    test('should manage subscriptions', async ({ page }) => {
        // Switch to Subscriptions tab
        await page.click('span:has-text("我的订阅")');

        // Add new subscription
        await page.click('button:has-text("添加订阅")');
        await page.fill('input[placeholder="技术主题..."]', 'Playwright');
        await page.click('.ant-modal-footer button.ant-btn-primary');

        await expect(page.getByText('订阅成功')).toBeVisible();
    });
});
