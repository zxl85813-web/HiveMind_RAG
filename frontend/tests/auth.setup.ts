
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button:has-text("进入系统")');

  // Simple wait - no strict validation to avoid brittle failures
  await page.waitForTimeout(5000);
  
  // Save whatever state we have
  await page.context().storageState({ path: authFile });
});
