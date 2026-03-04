import { test, expect } from '@playwright/test';

test.describe('Knowledge Management Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/knowledge');
    });

    test('should display knowledge base list and search', async ({ page }) => {
        // Verify title
        await expect(page.locator('h1')).toContainText('知识库管理');

        // Count items in list (Expected 25 from mock)
        const items = page.locator('.ant-list-item');
        await expect(items).toHaveCount(25);

        // Test detail drawer opening
        await items.first().click();
        const drawerTitle = page.locator('.ant-drawer-title');
        await expect(drawerTitle).toBeVisible();

        // Verify document table inside drawer
        const docTable = page.locator('.ant-table-tbody');
        await expect(docTable).toBeVisible();
    });

    test('should open create modal and validate form', async ({ page }) => {
        await page.click('button:has-text("创建知识库")');
        const modal = page.locator('.ant-modal-content');
        await expect(modal).toBeVisible();

        // Submit empty form to check validation
        await page.click('.ant-modal-footer button.ant-btn-primary');
        await expect(page.locator('.ant-form-item-explain-error')).toBeVisible();
    });
});
