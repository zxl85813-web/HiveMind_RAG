import { test, expect } from '@playwright/test';

test.describe('Creation Studio Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/studio');
    });

    test('should guide user through artifact generation', async ({ page }) => {
        // 1. Select Knowledge Base
        await page.click('.ant-select-selector');
        await page.click('.ant-select-item-option-content:has-text("HiveMind 核心架构")');

        // 2. Enter Task
        await page.fill('textarea[placeholder*="e.g. Generate"]', '生成一份系统架构说明文档');

        // 3. Start Generation
        await page.click('button:has-text("Start Generation")');

        // 4. Verify Pipeline Steps activate
        const steps = page.locator('.ant-steps-item-process');
        await expect(steps).toBeVisible();

        // 5. Wait for result (Simulation takes ~2s in mock)
        await expect(page.getByText('Generation Complete!')).toBeVisible({ timeout: 10000 });

        // 6. Verify result table
        await expect(page.locator('table')).toBeVisible();
    });
});
