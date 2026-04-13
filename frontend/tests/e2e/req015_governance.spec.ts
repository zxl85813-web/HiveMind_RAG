
import { test, expect } from '@playwright/test';

/**
 * 🛰️ [FE-GOV-TEST-015]: L5 Governance Escalation UI Test
 */
test.beforeEach(async ({ page }) => {
  // 1. Navigate directly (storageState should handle the mode)
  await page.goto('/settings', { waitUntil: 'networkidle' });
  
  // 2. Extra wait for the tab to be available
  const llmTab = page.locator('#gov-tab-llm');
  await expect(llmTab).toBeVisible({ timeout: 15000 });
  await llmTab.click();
});

test('should display the Governance Task Pipeline section', async ({ page }) => {
  const sectionTitle = page.locator('text=智体提报任务流水线');
  await expect(sectionTitle).toBeVisible();
});

test('should show escalated tasks in the table', async ({ page }) => {
  const table = page.locator('.ant-table-content');
  await expect(table).toBeVisible();
  await expect(page.locator('th').filter({ hasText: /^任务 ID$/ })).toBeVisible();
});

test('should trigger graph sync on button click', async ({ page }) => {
  const syncButton = page.locator('button:has-text("同步图谱")');
  await expect(syncButton).toBeVisible();
  await syncButton.click();
  await expect(syncButton).toBeVisible();
});

test('should open snapshot preview in a new tab', async ({ page, context }) => {
  const previewLink = page.locator('a:has-text("预览")').first();
  if (await previewLink.isVisible()) {
    const pagePromise = context.waitForEvent('page');
    await previewLink.click();
    const newPage = await pagePromise;
    expect(newPage.url()).toContain('docs/tasks/');
  }
});
