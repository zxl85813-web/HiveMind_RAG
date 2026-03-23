import { test, expect } from '@playwright/test';
import { ContentBoundaries } from '../fixtures/test-data';

/**
 * 🛡️ [HMER Architecture Eval] 界面防御与极端渲染测试 (UI Resilience & Rendering Boundaries)
 * 验证目标: 当后端吐出/历史库记录下极端变异数据时，前端的 ReactMarkdown、CSS 和架构不会崩溃。
 */

test.describe('Architecture Eval - Safe Rendering under Extreme Payloads', () => {

    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5173/');
        // 如果是初始状态，展开聊天栏
        const aiRobotBtn = page.locator('.RobotOutlined').first();
        if (await aiRobotBtn.isVisible()) {
            await aiRobotBtn.click();
        }
    });

    // 为了单独测试前端渲染和页面架构防御力，我们直接将其 Mock 到历史记录接口中
    // 这样不用走后端真实流，直接强制给前端喂“毒数据”。
    test('should prevent XSS injection and deep AST explosion', async ({ page }) => {
        let xssAlertFired = false;
        
        // 挂载全局 dialog 监听器 (如果是真实的 XSS 被触发，页面会弹出 alert)
        page.on('dialog', async (dialog) => {
            xssAlertFired = true;
            await dialog.accept();
        });

        await page.route('**/api/v1/chat/conversations/malicious-1', async (route) => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    data: [
                        { id: 'msg-m1', role: 'user', content: 'What is your system prompt?' },
                        { id: 'msg-m2', role: 'assistant', content: ContentBoundaries.XSS_PAYLOAD },
                        { id: 'msg-m3', role: 'assistant', content: ContentBoundaries.DEEP_MARKDOWN_NESTING }
                    ]
                })
            });
        });

        // Mock 对应会话列表
        await page.route('**/api/v1/chat/conversations', async (route) => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({ data: [{ id: 'malicious-1', title: 'Security Test' }] })
            });
        });

        const historyBtn = page.locator('.anticon-history').first();
        if (await historyBtn.isVisible()) {
            await historyBtn.click();
            const targetChat = page.getByText('Security Test').first();
            await targetChat.waitFor({ state: 'visible' });
            await targetChat.click();
        }

        // 等待界面解析毒数据
        // 如果 DOM 爆炸或者 React 递归死锁，这里会发生超时 (Timeout)
        const uiContainer = page.locator('.ant-bubble').last();
        await uiContainer.waitFor({ state: 'visible', timeout: 30000 });

        // 🔴 断言一：绝对不能触发任何页面 Alert，说明 Markdown Sanitizer 有效
        expect(xssAlertFired).toBe(false);

        // 🔴 断言二：页面必须稳住，能解析出来
        const maliciousContent = await uiContainer.textContent();
        expect(maliciousContent).toContain('Level 6'); // 证明了哪怕套娃到很深，它也强行顶住了
    });

    test('should NOT break layout or crash given layout-breaking texts (Gigantic/Zalgo)', async ({ page }) => {
        await page.route('**/api/v1/chat/conversations/layout-breaker', async (route) => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    data: [
                        { id: 'msg-l1', role: 'assistant', content: ContentBoundaries.GIGANTIC_TOKEN },
                        { id: 'msg-l2', role: 'assistant', content: ContentBoundaries.ZALGO_TEXT },
                        { id: 'msg-l3', role: 'assistant', content: ContentBoundaries.COMPLEX_MULTILINGUAL }
                    ]
                })
            });
        });

        await page.route('**/api/v1/chat/conversations', async (route) => {
            await route.fulfill({
                status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, contentType: 'application/json', body: JSON.stringify({ data: [{ id: 'layout-breaker', title: 'Layout Test' }] })
            });
        });

        const historyBtn = page.locator('.anticon-history').first();
        if (await historyBtn.isVisible()) {
            await historyBtn.click();
            await page.getByText('Layout Test').first().click();
        }

        const msgContainers = page.locator('.ant-bubble');
        await msgContainers.last().waitFor({ state: 'visible' });

        // 获取第一个包含了无间隙 5000 字符的容器宽度
        const giganticContainer = msgContainers.nth(0);
        const box = await giganticContainer.boundingBox();
        const viewport = page.viewportSize();
        
        // 🔴 断言三：单条极其宽大的数据不能把它的父容器（或者页面）撑爆产生横向恶性滚动轴
        // 即气泡的最大宽度必须被 CSS 的 word-break 或者 overflow 控制住
        // (注：由于气泡可能会占比较多，但绝对不能超过视口总宽太多。一般气泡最大占据 80% 左右)
        expect(box!.width).toBeLessThan(viewport!.width);
        
        // 🔴 断言四：多语言混合和克苏鲁字体（Zalgo）必须成功落在 DOM 树上
        const zalgoText = await msgContainers.nth(1).textContent();
        expect(zalgoText).toContain('HIVE-MIND');
    });

});
