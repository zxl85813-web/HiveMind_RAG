import { test, expect } from '@playwright/test';

/**
 * 🌀 [HMER Architecture Eval] 网络混沌工程与流式韧性矩阵 (Chaos Matrix)
 * 验证目标: 拦截并篡改 SSE 流，注入畸形 JSON 与触发 HTTP 风暴，评估前端架构的防崩溃与重连降级能力。
 */

test.describe('Architecture Eval - Stream Chaos Engineering', () => {
    test.beforeEach(async ({ page }) => {
        // [Browser-Debug]: 将浏览器内部日志重定向到 CI 终端
        page.on('console', msg => {
            if (msg.type() === 'error' || msg.text().includes('[StreamManager]')) {
                console.log(`[Browser ${msg.type().toUpperCase()}] ${msg.text()}`);
            }
        });

        await page.goto('/');
        await page.waitForLoadState('domcontentloaded');
    });

    test('Scenario 1: Payload Fuzzing - 畸形 JSON 注入不应导致页面白屏', async ({ page }) => {
        console.log('[Chaos] Intercepting SSE stream to inject malformed JSON payloads...');

        // 拦截底线的问答 API (使用通配符匹配各种 BaseURL 格式)
        await page.route('**/*chat/completions', async (route) => {
            const headers = {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            };

            // 构造毒化流 (Poisoned Stream)
            // 第一块正常，第二块残缺(少个大括号)，第三块正常，最后完成。
            const maliciousBody = 
                `data: {"track": "content", "type": "content", "delta": "This is a "}\n\n` +
                // ⚠️ 注意下方是一个只有一半的畸形 JSON
                `data: {"track": "content", "type": "con\n\n` + 
                `data: {"track": "content", "type": "content", "delta": "resilient test."}\n\n` +
                `data: {"track": "done", "type": "done"}\n\n`;

            await route.fulfill({ headers, body: maliciousBody });
        });

        const chatInput = page.getByPlaceholder(/在这里问我|Ask me anything/i);
        await chatInput.fill('Fuzz me!');
        await page.keyboard.press('Enter');

        // 验证前端不会因为 JSON.parse() 在中间块抛出错误而导致整个大组件树崩溃甚至白屏
        // 我们期望看到正常的 "This is a " 和 "resilient test." 被正确拼接，残缺的那一块被 try-catch 静默吞掉并打入控制台警告
        const aiResponse = page.locator('.chat-message.assistant').last();

        // 确保虽然接到了有毒数据，流依旧能够活到结束（内容能被正确渲染）
        await expect(aiResponse).toContainText('This is a', { timeout: 30000 });
        await expect(aiResponse).toContainText('resilient test.', { timeout: 30000 });
        
        console.log('[Metrics] Malformed JSON successfully isolated. Component survived the crash!');
    });

    test('Scenario 2: HTTP 429 Storm & Exponential Backoff - 连续限流与自我修复', async ({ page }) => {
        console.log('[Chaos] Simulating a massive 429 (Too Many Requests) storm from the server...');

        let requestCount = 0;
        const requestTimestamps: number[] = [];

        // 屏蔽前三次请求，故意给一个 429
        await page.route('**/*chat/completions', async (route) => {
            requestCount++;
            requestTimestamps.push(Date.now());
            
            if (requestCount <= 3) {
                // 连续 3 次无情决绝
                await route.fulfill({
                    status: 429,
                    contentType: 'application/json',
                    body: JSON.stringify({ detail: 'Rate Limit Exceeded from Chaos Mesh' })
                });
            } else {
                // 第 4 次终于放行
                await route.fulfill({
                    headers: { 'Content-Type': 'text/event-stream', 'Access-Control-Allow-Origin': '*' },
                    body: `data: {"track": "content", "type": "content", "delta": "I survived the rate limit storm!"}\n\n` +
                          `data: {"track": "done", "type": "done"}\n\n`
                });
            }
        });

        const chatInput = page.getByPlaceholder(/在这里问我|Ask me anything/i);
        await chatInput.fill('Test 429 Storm Retry Logic');
        
        const startTime = Date.now();
        await page.keyboard.press('Enter');

        const aiResponse = page.locator('.chat-message.assistant').last();
        await expect(aiResponse).toContainText('survived', { timeout: 30000 }); // 给足时间让它重试 3 次

        // 深入验证指数退避算法 (Exponential Backoff) 是否真的被执行了！
        expect(requestCount).toBeGreaterThanOrEqual(4);

        if (requestTimestamps.length >= 3) {
            // 计算每次重试的间隔
            const gap1 = requestTimestamps[1] - requestTimestamps[0]; // 第2次和第1次的差值
            const gap2 = requestTimestamps[2] - requestTimestamps[1]; // 第3次和第2次的差值
            
            console.log(`[Metrics] Retry Interval 1: ${gap1}ms`);
            console.log(`[Metrics] Retry Interval 2: ${gap2}ms`);
            
            // 指数退避的本质是每次间隔都要越来越长，而不是每次无脑死命发起请求 (防雪崩)
            expect(gap2).toBeGreaterThan(gap1);
        }

        console.log('[Metrics] LLM Health Monitor correctly handled degraded states and recovered execution!');
    });
});
