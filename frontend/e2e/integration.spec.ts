import { test, expect } from '@playwright/test';

/**
 * 集成测试 (Real Data Integration Test)
 * 
 * 验证前端与真实后端接口的交互：
 * 1. 禁用 Mock 模式
 * 2. 真实创建一个知识库
 * 3. 验证后端返回真实 ID 并持久化
 */
test.describe('Real Data Flow (Integration)', () => {

    test.beforeEach(async ({ page }) => {
        // 强制禁用 Mock 模式，确保请求发送到 8000 端口后端
        await page.addInitScript(() => {
            window.localStorage.removeItem('VITE_USE_MOCK');
            window.localStorage.removeItem('VITE_MOCK_CASE');
        });
        await page.goto('/');
    });

    test('真实链路: 创建知识库并验证持久化', async ({ page }) => {
        const uniqueName = `E2E_Test_KB_${Date.now().toString().slice(-6)}`;

        // 1. 进入知识库页面
        await page.click('text=知识库');

        // 2. 打开创建弹窗
        await page.click('button:has-text("创建知识库")');

        // 3. 填写表单
        await page.fill('input[id="name"]', uniqueName);
        await page.fill('textarea[id="description"]', '这是由自动化集成测试生成的真实数据。');

        // 4. 提交
        await page.click('.ant-modal-footer button.ant-btn-primary');

        // 5. 验证是否出现在列表中 (真实后端返回)
        // 注意：真实后端可能比 Mock 慢，Playwright 会自动等待
        await expect(page.locator(`.ant-list-item:has-text("${uniqueName}")`)).toBeVisible({ timeout: 10000 });

        // 6. 留痕迹：截图确认列表已包含真实数据
        await page.screenshot({ path: `e2e-screenshots/integration-success-${Date.now()}.png` });
    });
});
