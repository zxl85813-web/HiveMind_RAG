import { test, expect } from '@playwright/test';

/**
 * 🛰️ [HMER Phase 3] Verification: Stream Resilience & MultiTrack
 * 验证目标: 在流生成期间断开网络又恢复，AI应该能成功通过 _resume_index 续接生成。
 */

test.describe('Phase 3: Resilient Streaming & Multi-Track Parsing', () => {
    test.beforeEach(async ({ page }) => {
        // 开发环境路径
        await page.goto('http://localhost:5173/');
    });

    test('should survive a 3-second network loss and complete generation with no data loss', async ({ context, page }) => {
        // 1. 发起一个长文本请求 (容易在中途打断)
        const chatInput = page.locator('textarea[placeholder*="输入消息"]');
        await chatInput.fill('Please write a detailed 3-paragraph essay about the history of artificial intelligence.');
        await page.keyboard.press('Enter');

        // 2. 等待 TTFT (Time To First Token)
        // 寻找包含 AI 回复的容器
        const lastMessage = page.locator('.chat-message.assistant').last();
        await lastMessage.waitFor({ state: 'visible', timeout: 30000 });
        
        // 当看到第一段内容生成时
        await expect(lastMessage).toContainText(/\w+/, { timeout: 10000 });
        const contentBeforeDrop = await lastMessage.textContent();
        
        // 3. 混沌工程：断开网络 3 秒
        console.log('[Chaos] Network Dropped!');
        await context.setOffline(true);
        await page.waitForTimeout(3000); // 3秒网络空窗期
        
        // 4.恢复网络，预期内部 StreamManager 会使用 _resume_index 重新建立连接
        console.log('[Chaos] Network Restored!');
        await context.setOffline(false);
        
        // 5. 等待生成事件结束 (done事件)
        // 这个 locator 的选择取决于 UI 如何表示流状态
        await page.waitForSelector('.ai-message-complete', { timeout: 60000 }); 
        
        const contentAfterCompletion = await lastMessage.textContent();

        // 断言：
        // a. 断网前的内容没有被清空 (依然存在)
        expect(contentAfterCompletion).toContain(contentBeforeDrop?.trim());
        
        // b. 整体长度有了明显增加 (断点续传成功补全了文章)
        expect(contentAfterCompletion!.length).toBeGreaterThan(contentBeforeDrop!.length);
        
        console.log(`[Result] Essay Length Before: ${contentBeforeDrop?.length}, After: ${contentAfterCompletion?.length}`);
    });

    test('should correctly parse the "thinking" track and display as metadata', async ({ page }) => {
        // 验证多轨解析：请求一个会调用 <think> 分析的问题
        const chatInput = page.locator('textarea[placeholder*="输入消息"]');
        await chatInput.fill('Please think step by step: what is 123 * 456?');
        await page.keyboard.press('Enter');

        // 等待带有思考块的 UI 渲染 (比如一个 collapse 容器)
        // 具体选择器需要根据 UI 实际实现进行调整
        const thinkingContainer = page.locator('.ai-thinking-log').last();
        await thinkingContainer.waitFor({ state: 'visible', timeout: 30000 });

        const thinkText = await thinkingContainer.textContent();
        expect(thinkText?.length).toBeGreaterThan(5); // 确保里面真的解析出了思考过程
    });
});
