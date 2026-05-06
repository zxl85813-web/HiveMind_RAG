import { test, expect } from '@playwright/test';

// Force the test context to use Chinese locale for reliable text assertions
test.use({ locale: 'zh-CN' });

// Dynamically use BASE_URL from environment variable, defaulting to localhost
const targetURL = process.env.BASE_URL || 'http://localhost:5173';

test.describe('HiveMind Production Verification E2E Test (zh-CN)', () => {
    test.beforeEach(async ({ page }) => {
        // Go to the target application URL
        await page.goto(targetURL);
        // Wait for the app to settle
        await page.waitForTimeout(1000);
    });

    test('Should render ChatPanel in default AI Mode without crashing', async ({ page }) => {
        // 1. Verify that the AI Assistant panel is fully rendered
        await expect(page.getByText('AI 助手')).toBeVisible();

        // 2. Verify that the empty state welcome title is rendered
        await expect(page.getByText('HiveMind AI')).toBeVisible();

        // 3. Verify that the Chat input area is ready with the correct Chinese placeholder
        const inputArea = page.getByPlaceholder('在这里问我任何问题...');
        await expect(inputArea).toBeVisible();

        // 4. Verify that there is no error boundary on page load (our .map fix was successful!)
        const errorBoundary = page.locator('.ant-result-error');
        await expect(errorBoundary).not.toBeVisible();
    });

    test('Should be able to toggle to Classic Mode and verify Sidebar', async ({ page }) => {
        // 1. Toggle to Classic Mode (传统模式)
        const classicModeBtn = page.getByRole('button', { name: '传统模式' }).or(page.locator('button:has-text("传统模式")'));
        await expect(classicModeBtn).toBeVisible();
        await classicModeBtn.click();
        await page.waitForTimeout(500);

        // 2. Once in Classic Mode, the Sidebar becomes visible. Verify logo text and status.
        // Resolve strict-mode violation by using .first()
        await expect(page.locator('span:has-text("HiveMind")').first()).toBeVisible();
        await expect(page.getByText('Online')).toBeVisible();

        // 3. Switch back to AI Mode
        const aiModeBtn = page.getByRole('button', { name: 'AI 模式' }).or(page.locator('button:has-text("AI 模式")'));
        await expect(aiModeBtn).toBeVisible();
        await aiModeBtn.click();
    });

    test('Should navigate to System Settings and render successfully in Classic Mode', async ({ page }) => {
        // 1. Toggle to Classic Mode (传统模式) to expose the sidebar navigation
        const classicModeBtn = page.getByRole('button', { name: '传统模式' }).or(page.locator('button:has-text("传统模式")'));
        await expect(classicModeBtn).toBeVisible();
        await classicModeBtn.click();
        await page.waitForTimeout(500);

        // 2. Click on "系统设置" (System Settings) in the sidebar
        const settingsLink = page.locator('text=系统设置').or(page.locator('span:has-text("系统设置")'));
        await expect(settingsLink).toBeVisible();
        await settingsLink.click();

        // 3. Verify page navigation has occurred and System Settings are rendered correctly
        await expect(page).toHaveURL(/.*settings/);
        await expect(page.getByText('LLM 模型设置').or(page.getByText('LLM Model Configuration'))).toBeVisible();
    });
});
