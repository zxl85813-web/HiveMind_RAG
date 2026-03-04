import { test, expect } from '@playwright/test';

test.describe('System Settings Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/settings');
    });

    test('should allow configuring LLM and Agent parameters', async ({ page }) => {
        await expect(page.getByText('系统设置')).toBeVisible();

        // Test Select component
        await page.locator('.ant-select-selector').first().click();
        await page.click('.ant-select-item-option-content:has-text("GPT-4o")');

        // Test Switches
        const switches = page.locator('.ant-switch');
        await expect(switches).toHaveCount(2);
        await switches.first().click();

        // Test Input.Password
        const passwordInput = page.locator('input[type="password"]').first();
        await passwordInput.fill('sk-test-key-12345');
        await expect(passwordInput).toHaveValue('sk-test-key-12345');
    });
});
