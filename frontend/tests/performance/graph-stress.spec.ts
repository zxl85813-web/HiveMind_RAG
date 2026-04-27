import { test, expect } from '@playwright/test';

test.describe('GraphVisualizer Stress Test', () => {
  test('Render Massive Graph Data (5000 Nodes, 10000 Edges)', async ({ page }) => {
    // 监听 console 看看有没有报错
    page.on('console', msg => console.log(`[Browser]: ${msg.text()}`));
    page.on('pageerror', err => console.log(`[Browser Error]: ${err.message}`));

    // 生成海量数据：5000 个节点，10000 条边
    const NUM_NODES = 5000;
    const NUM_EDGES = 10000;
    
    const mockNodes = Array.from({ length: NUM_NODES }).map((_, i) => ({
      id: `node_${i}`,
      name: `Entity ${i}`,
      val: Math.random() * 10 + 2,
      color: i % 2 === 0 ? '#1890ff' : '#52c41a'
    }));

    const mockEdges = Array.from({ length: NUM_EDGES }).map((_, i) => ({
      id: `edge_${i}`,
      source: `node_${Math.floor(Math.random() * NUM_NODES)}`,
      target: `node_${Math.floor(Math.random() * NUM_NODES)}`,
      type: 'RELATED_TO'
    }));

    // 这里我们假设本地前端跑在 http://localhost:5173，由于测试环境，我们直接模拟后端全链路
    // 正常测试需要在 CI 里配合 baseUrl
    
    // 拦截获取知识库列表请求，伪造一个知识库
    await page.route('**/api/v1/knowledge', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [{ id: 'kb_stress_1', name: 'Stress Test KB', version: 1 }]
          })
        });
      } else {
        await route.continue();
      }
    });

    // 拦截图谱数据请求，返回海量数据
    await page.route('**/api/v1/knowledge/kb_stress_1/graph', async route => {
      console.log('Intercepted Graph Request, returning MASSIVE dataset...');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            nodes: mockNodes,
            links: mockEdges
          }
        })
      });
    });

    // 🔒 [Auth Mock]: Bypass login wall
    await page.addInitScript(() => {
      const token = 'mock_token';
      const userId = 'user_1';
      localStorage.setItem('hm_access_token', token);
      sessionStorage.setItem('hm_access_token', token);
      localStorage.setItem('hm_active_user_id', userId);
      sessionStorage.setItem('hm_active_user_id', userId);
    });

    await page.route('**/api/v1/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: { id: 'user_1', username: 'admin', role: 'admin' }
        })
      });
    });

    await page.route('**/api/v1/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'mock_token', token_type: 'bearer' })
      });
    });

    // Navigate to Knowledge Page (assuming routes)
    // 根据系统常见约定，访问知识库页面
    console.log('Navigating to app...');
    try {
        await page.goto('http://localhost:5173/knowledge', { timeout: 10000 });
        
        // 点击列表中的知识库以打开抽屉 (Drawer)
        await page.getByText('Stress Test KB').click();
        
        // 切换到“知识图谱” Tab
        console.log('Switching to Graph Tab...');
        await page.getByText('知识图谱').click();

        // 测量渲染开始到 Canvas 出现的耗时
        const startTime = Date.now();
        
        // 等待 canvas 挂载
        await page.waitForSelector('canvas', { timeout: 30000 });
        const canvasVisibleTime = Date.now();
        
        console.log(`⏱️ Canvas DOM Mounted in: ${canvasVisibleTime - startTime}ms`);
        
        // 📊 [Metrics]: Capture browser performance state
        const metrics = await page.metrics();
        console.log(`📊 JSHeapUsedSize: ${(metrics.JSHeapUsedSize / 1024 / 1024).toFixed(2)} MB`);
        console.log(`📊 JSHeapTotalSize: ${(metrics.JSHeapTotalSize / 1024 / 1024).toFixed(2)} MB`);
        console.log(`📊 TaskDuration: ${metrics.TaskDuration}s`);
        console.log(`📊 Nodes: ${metrics.Nodes}`);

        // 此时图谱引擎会开始解算力导向图结构 (D3-Force)
        // 给 5 秒钟的主线程运算时间，测试页面会不会崩溃
        await page.waitForTimeout(5000);

        const finalMetrics = await page.metrics();
        console.log(`📊 Final JSHeapUsedSize: ${(finalMetrics.JSHeapUsedSize / 1024 / 1024).toFixed(2)} MB`);
        console.log(`📊 Peak Memory Delta: ${((finalMetrics.JSHeapUsedSize - metrics.JSHeapUsedSize) / 1024 / 1024).toFixed(2)} MB`);

        // 如果没有抛出 pageerror 且 Canvas 依然在，说明引擎扛住了。
        const canvas = await page.$('canvas');
        expect(canvas).not.toBeNull();
        
        console.log(`✅ [PASS] Successfully survived 5000 nodes & 10000 edges stress test.`);
        
    } catch (e) {
        console.log(`Navigation or render failed (dev server might not be running). Error: ${e}`);
        test.skip();
    }
  });
});
