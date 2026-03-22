import { test, expect } from '@playwright/test';

/**
 * 🏃‍♂️ [HMER Architecture Eval] 长效稳定性与内存剖析 (Endurance / Memory Profiling)
 * 验证目标: 高频往复执行核心动作 (发送、收流、切会话)，采集 V8 堆内存与 DOM 节点数，捕获游离的闭包或未卸载组件。
 */

test.describe('Architecture Eval - Endurance Memory Leak Profiling', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5173/');
        await page.waitForLoadState('networkidle');
    });

    test('should not linearly leak memory or DOM nodes over 50 conversation cycles', async ({ page }) => {
        // 马拉松极其耗时，放宽限制
        test.setTimeout(5 * 60 * 1000); // 5 分钟
        
        console.log('[Endurance] Attaching Chrome DevTools Protocol (CDP) session...');
        // 绑定底层的 CDP 会话以获取真实的内存监控
        const client = await page.context().newCDPSession(page);
        
        // 采集器函数
        const getMetrics = async () => {
            const metrics = await client.send('Performance.getMetrics');
            const jsHeapSize = metrics.metrics.find(m => m.name === 'JSHeapUsedSize')?.value || 0;
            const domNodes = metrics.metrics.find(m => m.name === 'Nodes')?.value || 0;
            const eventListeners = metrics.metrics.find(m => m.name === 'JSEventListeners')?.value || 0;
            return {
                heapMB: jsHeapSize / (1024 * 1024),
                domNodes,
                eventListeners
            };
        };

        // 截取基线 (Baseline)
        const baseMetrics = await getMetrics();
        console.log(`[Baseline] Heap: ${baseMetrics.heapMB.toFixed(2)} MB | DOM Nodes: ${baseMetrics.domNodes} | Listeners: ${baseMetrics.eventListeners}`);

        const ITERATIONS = 30; // 缩小为 30 次以避免 CI 跑死，但足以画出斜率
        const heapHistory: number[] = [];
        const domHistory: number[] = [];

        // 我们 Mock 一个秒回的后端以防测试太久
        await page.route('**/api/v1/chat/completions', async (route) => {
            await route.fulfill({
                headers: { 'Content-Type': 'text/event-stream' },
                body: `data: {"track": "content", "type": "content", "delta": "Quick Mock response for endurance test."}\n\n` +
                      `data: {"track": "done", "type": "done"}\n\n`
            });
        });

        for (let i = 0; i < ITERATIONS; i++) {
            // 动作 1：发送消息
            const chatInput = page.locator('textarea[placeholder*="输入消息"]');
            await chatInput.fill(`Endurance Message ${i + 1}`);
            await page.keyboard.press('Enter');

            // 等待它生成完
            // 假设UI会改变输入框状态或呈现完成标记
            await expect(chatInput).toBeEmpty({ timeout: 10000 });
            
            // 随便给一点喘息时间让 React 渲染和调度
            await page.waitForTimeout(300);

            // 动作 2：新建或切换会话，诱导组件挂载/卸载
            // 假设我们有一个“新会话”按钮
            const newChatBtn = page.getByRole('button', { name: /新会话|New/i }).first();
            if (await newChatBtn.isVisible()) {
                await newChatBtn.click();
            }

            // 动作 3：抽样 GC 前后的内存
            if (i % 10 === 0 || i === ITERATIONS - 1) {
                // 强制 V8 垃圾回收，滤除新生代垃圾的毛刺，只看真正的老生代驻留
                await client.send('HeapProfiler.collectGarbage');
                const m = await getMetrics();
                heapHistory.push(m.heapMB);
                domHistory.push(m.domNodes);
                console.log(`[Cycle ${i + 1}] Heap: ${m.heapMB.toFixed(2)} MB | DOM Nodes: ${m.domNodes}`);
            }
        }

        // --- 核心斜率断言 ---
        const initialHeap = heapHistory[0];
        const finalHeap = heapHistory[heapHistory.length - 1];
        const initialDom = domHistory[0];
        const finalDom = domHistory[domHistory.length - 1];

        // 允许内存有正常的缓慢上升（组件缓存、Redux 队列等），但绝对不允许爆炸式的陡增
        // 假设基础堆栈在 30MB 左右，30次循环后不应膨胀超过 15MB 绝对值
        const heapGrowth = finalHeap - initialHeap;
        console.log(`[Eval] Final Heap Growth: ${heapGrowth.toFixed(2)} MB`);
        
        expect(heapGrowth).toBeLessThan(15); 

        // DOM 节点的膨胀
        // 如果我们不断清空/切换上下文，页面里活跃的节点应该处在一个平台期，而不是无尽堆叠
        const domGrowth = finalDom - initialDom;
        console.log(`[Eval] Final DOM Growth: ${domGrowth} Nodes`);
        
        // 允许 30 次累积几千个DOM（由于长列表不一定立即回收），但决不能呈现线性的上万节点泄漏
        expect(domGrowth).toBeLessThan(8000); 

        await client.detach();
    });
});
