import { test, expect } from '@playwright/test';

/**
 * 📡 [HMER Architecture Eval] 极限遥测对账审计 (Telemetry Integrity)
 * 验证目标: 在 AI 生成期间或刚结束时暴力关闭页面 / 刷新，验证退出埋点是否发生了“掉单”。
 */

test.describe('Architecture Eval - Telemetry Integrity Audit', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5173/');
        await page.waitForLoadState('networkidle');
    });

    test('should successfully dispatch telemetry beacon even when page is violently closed during or exactly after stream Generation', async ({ browser }) => {
        // 创建一个全新的独立上下文 (Context)，以确保不受其它测试污染
        const context = await browser.newContext();
        const page = await context.newPage();
        
        console.log('[Audit] Setup telemetry interceptors on the Context level (survives page flush)...');
        
        let beaconCaptured = false;
        let beaconPayload: any = null;

        // 使用 Context 级别的 listener，因为 page.close() 后可能就听不见 page.on('request') 了
        // 这恰好是 SendBeacon 为什么如此必要的原因：它让浏览器主进程接管发送
        context.on('request', (request) => {
            if (request.url().includes('/api/v1/telemetry') && request.method() === 'POST') {
                beaconCaptured = true;
                beaconPayload = request.postDataJSON();
                console.log('[Audit] Beacon Caught on Context Loop Escape:', beaconPayload);
            }
        });

        await page.goto('http://localhost:5173/');
        
        // 缩短耗时：我们自己拦截并魔改流的返回速度
        await page.route('**/api/v1/chat/completions', async (route) => {
            const headers = { 'Content-Type': 'text/event-stream' };
            const fastStream = 
                `data: {"track": "content", "type": "content", "delta": "I am about to close my "}\n\n` +
                // 此时前端已拿到首个 Token (TTFT) 并准备埋点，但在那 1ms，我们就会直接执行 page.close()
                `data: {"track": "content", "type": "content", "delta": "eyes forever!"}\n\n` +
                `data: {"track": "done", "type": "done", "latency_ms": 350}\n\n`;
                
            await route.fulfill({ headers, body: fastStream });
        });

        // 1. 发起对话触发 TTFT
        const chatInput = page.getByPlaceholder(/在这里问我|Ask me anything/i);
        await chatInput.fill('Trigger my final beacon.');
        await page.keyboard.press('Enter');

        // 2. 致命打击：不等 UI 加载好，直接把标签页强杀！
        // 这一步必须非常快，这就是真实世界的“刚拿到数据就滑走”
        await page.waitForTimeout(100); // 100ms 足够发起 fetchEventSource 的建联了
        console.log('[Chaos] Violently closing the tab mid-flight!');
        await page.close();
        
        // 我们等个几毫秒让底层的网络调度器收敛
        await new Promise(resolve => setTimeout(resolve, 500));

        // 3. 对账 (Reconciliation)
        // 这个断言非常硬核：如果前端的 MonitorService 是挂在普通的 setTimeout 里，那绝对发不出去
        // 只有像 navigator.sendBeacon(url, data) 或者 fetch(url, { keepalive: true }) 才能确保发出去
        expect(beaconCaptured).toBe(true);

        // 检查 payload 是否合格
        if (beaconPayload) {
            expect(beaconPayload).toHaveProperty('type');
            // 断言有特定的性能字段
            expect(beaconPayload).toHaveProperty('payload.ttft_ms');
            console.log('[Metrics] Beacon payload cleanly survived the page crash!');
        } else {
            console.warn('[Warning] Although request matched url pattern, payload could not be parsed as JSON. It might be due to sendBeacon using Blob or FormData payload formats.');
        }

        await context.close();
    });
});
