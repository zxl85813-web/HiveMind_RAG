import { test, expect } from '@playwright/test';

/**
 * 🛰️ [HMER Phase 2] Verification: Local Edge Engine
 * 验证目标: 页面刷新后，历史会话数据应从 IndexedDB 极速恢复，且不丢失数据。
 */

test.describe('Phase 2: Memory Persistence (IndexedDB)', () => {
  test.beforeEach(async ({ page }) => {
    // 假设使用本地开发服务器
    await page.goto('http://localhost:5173/');
    // 等待应用初始化
    await page.waitForLoadState('networkidle');
  });

  test('should persist conversation in IndexedDB and restore instantly on reload', async ({ page }) => {
    // 1. 发起一条全新对话
    const chatInput = page.locator('textarea[placeholder*="输入消息"]'); // 根据实际选择器调整
    await chatInput.fill('Hello, test persistence!');
    await page.keyboard.press('Enter');

    // 2. 等待 AI 回复完毕
    await page.waitForSelector('.ai-message-complete', { timeout: 15000 }); // 根据实际标志调整
    const originalMessageCount = await page.locator('.chat-message').count();
    
    // 3. 记录时间并强制刷新页面 (模拟离线加载或二次进入)
    const startTime = Date.now();
    await page.reload({ waitUntil: 'domcontentloaded' });
    
    // 4. 断言：历史列表应被迅速渲染 (通常 < 100ms，这里放宽一点给 Playwright 环境)
    // 等待侧边栏历史记录出现
    const historyItem = page.locator('.conversation-history-item').first();
    await historyItem.waitFor({ state: 'visible', timeout: 5000 });
    const restoreTime = Date.now() - startTime;
    
    // 验证性能假设
    console.log(`[Metrics] Conversation history restored in ${restoreTime}ms`);
    // 在真实用户设备上我们期望 <100ms，但在 E2E 测试环境我们断言它确实在合理时间内加载了
    expect(restoreTime).toBeLessThan(1500); // 即使在 Playwright 中，影子读取也应该很快

    // 5. 点击历史记录，验证正文是否还保留着
    await historyItem.click();
    await page.waitForSelector('.chat-message');
    const restoredMessageCount = await page.locator('.chat-message').count();
    
    expect(restoredMessageCount).toBe(originalMessageCount);
  });
});
