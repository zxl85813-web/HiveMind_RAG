import { test, expect } from '@playwright/test';

/**
 * 🛰️ [HMER Architecture Eval] 容量边界与性能退化测试 (IndexedDB 极限)
 * 验证目标: 注入海量数据后，评估页面的冷启动耗时以及主线程是否产生严重卡顿。
 */

test.describe('Architecture Eval - IndexedDB Capacity Stress Test', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5173/');
        await page.waitForLoadState('networkidle');
    });

    test('should handle 1,000 conversations and 5,000 messages without severe UI blocking', async ({ page }) => {
        test.setTimeout(120000); // 长耗时测试，放宽超时限制

        console.log('[Stress] Injecting 1,000 mock conversations directly into IndexedDB...');

        // 1. 通过页面注入脚本，直接向底层 `HMERDB` 爆破写入数据
        await page.evaluate(async () => {
            return new Promise((resolve, reject) => {
                // 打开我们在 LocalEdgeEngine.ts 建立的数据库
                const request = window.indexedDB.open('HMERDB');
                
                request.onerror = (e) => reject((e.target as any).error);
                request.onsuccess = (e) => {
                    const db = (e.target as any).result;
                    // 以 readwrite 模式打开关键表
                    const tx = db.transaction(['conversations', 'messages'], 'readwrite');
                    const convStore = tx.objectStore('conversations');
                    const msgStore = tx.objectStore('messages');

                    for (let i = 0; i < 1000; i++) {
                        const convId = `stress-conv-${i}`;
                        const title = `Load Test Conversation ${i}`;
                        const timestamp = Date.now() - (i * 10000);

                        // 注入会话元数据
                        convStore.put({
                            id: convId,
                            title: title,
                            updatedAt: timestamp,
                            createdAt: timestamp,
                            model: 'gpt-4o-mini'
                        });

                        // 注入 5 条庞大的随机历史消息
                        for (let j = 0; j < 5; j++) {
                            const padding = "A long chunk of text intended to consume local storage space and simulate huge payload. ".repeat(50);
                            msgStore.put({
                                id: `stress-msg-${i}-${j}`,
                                conversationId: convId,
                                role: j % 2 === 0 ? 'user' : 'assistant',
                                content: `Simulated message ${j} for ${convId}. ${padding}`,
                                createdAt: timestamp + j * 1000
                            });
                        }
                    }

                    tx.oncomplete = () => resolve(true);
                    tx.onerror = () => reject(tx.error);
                };
            });
        });

        console.log('[Stress] Injection complete. Hard reloading the page...');

        // 2. 挂载性能观测器 (PerformanceObserver) 以捕获 Long Task (超过 50ms 的主线程阻塞)
        // 这一步必须在 reload 之前植入
        await page.addInitScript(() => {
            window['__longTasks'] = [];
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    window['__longTasks'].push({
                        name: entry.name,
                        duration: entry.duration,
                        startTime: entry.startTime
                    });
                }
            });
            observer.observe({ entryTypes: ['longtask'] });
        });

        // 3. 强制冷启动加载
        const loadStartTime = Date.now();
        await page.reload({ waitUntil: 'domcontentloaded' });
        
        // 4. 等待长列表渲染完成 (例如侧边栏的会话列表)
        const firstHistoryItem = page.locator('.conversation-history-item').first();
        await firstHistoryItem.waitFor({ state: 'visible', timeout: 30000 });
        const coldBootTime = Date.now() - loadStartTime;
        
        console.log(`[Metrics] Application cold boot and list render took: ${coldBootTime}ms`);

        // 5. 提取并分析 Long Task 数据
        const longTasks = await page.evaluate(() => window['__longTasks']);
        
        // 我们主要关心的是与我们读取 IDB + 渲染列表相关的巨大阻塞
        const severeTasks = longTasks.filter((task: any) => task.duration > 150);
        
        console.log(`[Metrics] Encountered ${severeTasks.length} severe Long Tasks (>150ms) during boot.`);
        
        if (severeTasks.length > 0) {
            console.warn('[Warning] Main thread was heavily blocked. We might need Web Workers for IndexedDB reads or stricter Virtualization for the UI list.');
            for (const task of severeTasks) {
                console.warn(`         - Task blocked for ${task.duration.toFixed(2)}ms`);
            }
        }

        // 6. 硬核断言
        // 即便有 1000 条历史数据，加载这 1000 条的元数据并在 UI 虚拟列表中渲染出来，冷启动也不应挂掉，总体时长必须可接受
        expect(firstHistoryItem).toBeVisible();
        expect(coldBootTime).toBeLessThan(3500); // 即使在最差的 Playwright 注入沙盒中，也不应超过 3.5s
        
        // 断言最严重的主线程卡顿不该超过 500ms，否则用户会感到页面完全卡死
        const maxBlockTime = Math.max(0, ...severeTasks.map((t: any) => t.duration));
        expect(maxBlockTime).toBeLessThan(500); 
    });
});
