import { test, expect } from '@playwright/test';

test.describe('Agent Swarm Monitoring Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/agents');
    });

    test('should show live swarm metrics and agent cards', async ({ page }) => {
        // Check Stats Cards (Mock values)
        await expect(page.getByText('活跃 Agent')).toBeVisible();
        await expect(page.locator('.ant-statistic-content-value').filter({ hasText: '5' })).toBeVisible();

        // Check Agent Grid
        // Based on mockData.ts, should have 5 agents
        // Wait for list to load
        await expect(page.locator('.ant-card')).toHaveCount(9); // 4 stat cards + 5 agents
    });

    test('should switch between shared memory tabs', async ({ page }) => {
        // Default tab is TODOs
        await expect(page.getByText('共享任务队列')).toBeVisible();

        // Switch to Reflections
        await page.click('div[role="tab"]:has-text("自省日志")');
        await expect(page.getByText('自省洞察')).toBeVisible();

        // Verify list content
        await expect(page.locator('.memory-log-item')).toHaveCount(60);
    });
});
