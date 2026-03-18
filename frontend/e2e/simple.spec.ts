import { test, expect } from '@playwright/test';

test('simple load', async ({ page }) => {
    await page.goto('/');
    console.log('Title is:', await page.title());
    await expect(page).toHaveTitle(/HiveMind/);
});
