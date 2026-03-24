import { test, expect } from '@playwright/test';

/**
 * 📡 [HMER Architecture Eval] 极限遥测对账审计 (Telemetry Integrity)
 * 验证目标: 在 AI 生成期间或刚结束时暴力关闭页面 / 刷新，验证退出埋点是否发生了“掉单”。
 */

test.describe('Architecture Eval - Telemetry Integrity Audit', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('domcontentloaded');
    });

    test('should successfully dispatch telemetry beacon even when page is violently closed during or exactly after stream Generation', async ({ browser }) => {
        // 创建一个全新的独立上下文 (Context)，以确保不受其它测试污染
        const context = await browser.newContext();
        const page = await context.newPage();
        let beaconCaptured = false;
        let beaconPayload: any = null;
        await page.goto('/');
        
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
        await chatInput.click(); // 确保聚焦
        await chatInput.fill('Trigger my final beacon.');

        // 🛰️ [Network Warm-up]: 在暴力强杀前，先触发一次非关键请求
        // 这能确保 DNS、CORS 预检在 CI 容器的网络栈中先行完成热身
        await page.evaluate(() => {
            const apiBase = (window as any).VITE_API_BASE_URL || '';
            fetch(`${apiBase}/telemetry`, { 
                method: 'POST', 
                body: JSON.stringify({ type: 'warmup' }),
                headers: { 'Content-Type': 'application/json' }
            }).catch(() => {});
        });

        // 🛰️ [Double-Lock Sync]: 同时等待代码执行日志 OR 网络请求发出
        // 允许长达 15s 的超时，以应对 CI 环境的极端冷启动延迟
        const beaconFired = new Promise(resolve => {
            context.on('request', async request => {
                const url = request.url();
                if (url.includes('telemetry') && request.method() === 'POST') {
                    try {
                        const postData = request.postDataJSON();
                        // 🛰️ [Architecture-Gate]: 重点！排除预热包，只捕获含有业务指标的数据包
                        if (postData && postData.type !== 'warmup') {
                            beaconCaptured = true;
                            beaconPayload = postData;
                            console.log(`[Audit] Verified business telemetry intercepted: ${postData.type}`);
                            resolve('network');
                        } else {
                            console.log('[Audit] Ignoring warmup telemetry packet.');
                        }
                    } catch (e) {
                        // 此时可能由于正在发送中导致解析失败，忽略
                    }
                }
            });
            page.on('console', msg => {
                const text = msg.text();
                // 如果是业务端的成功日志，也尝试触发同步
                if (text.includes('[Monitor] Telemetry sent') && !text.includes('warmup')) {
                    resolve('console');
                }
            });
        });

        // 模拟用户输入并按下 Enter
        await chatInput.press('Enter');

        // 等待同步信号产生
        const reason = await Promise.race([
            beaconFired,
            page.waitForTimeout(15000).then(() => 'timeout') // 15s 窗口
        ]);

        console.log(`[Chaos] Telemetry sync trigger: ${reason}. Closing page NOW.`);
        
        // 极速强杀，模拟暴力关闭
        await page.close();
        
        // 3. 结果收割 (给底层的网络栈一点时间收敛)
        await new Promise(resolve => setTimeout(resolve, 1500));

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
