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
        const chatInput = page.getByRole('textbox', { name: /输入|Message/i }).first();
        if ((await chatInput.count()) === 0) {
            // fallback for missing aria-labels
            await page.locator('textarea').first().fill('Please write a detailed 3-paragraph essay about the history of artificial intelligence.');
        } else {
            await chatInput.fill('Please write a detailed 3-paragraph essay about the history of artificial intelligence.');
        }
        await page.keyboard.press('Enter');

        // 2. 等待 TTFT (Time To First Token)
        // 查找 Antd X 的气泡
        const lastMessage = page.locator('.ant-bubble').last();
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
        
        // 5. 等待生成事件结束
        // 我们通过检查是否可以再次发送消息（或者loading状态消失）来判断
        await expect(page.locator('textarea').first()).not.toBeDisabled({ timeout: 60000 }); 
        
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
        await page.locator('textarea').first().fill('Please think step by step: what is 123 * 456?');
        await page.keyboard.press('Enter');

        // 等待带有思考块的 UI 渲染 (Ant Design X ThoughtChain)
        const thinkingContainer = page.getByText(/🤔 内部思考|⚡/).last();
        await thinkingContainer.waitFor({ state: 'visible', timeout: 30000 });

        const thinkText = await thinkingContainer.textContent();
        expect(thinkText?.length).toBeGreaterThan(5); // 确保里面真的解析出了思考过程
    });
});
