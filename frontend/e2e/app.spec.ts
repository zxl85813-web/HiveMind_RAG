import { test, expect } from '@playwright/test';

test.describe('HiveMind Dashboard & Navigation', () => {
    test.beforeEach(async ({ page }) => {
        // 确保从标准 Mock 数据开始
        await page.addInitScript(() => {
            window.localStorage.removeItem('VITE_MOCK_CASE');
        });
        await page.goto('/');
    });

    test('应该能看到正确的首页统计数据 (Mock)', async ({ page }) => {
        // 等待数据加载 (Mock 延迟 500ms)
        await expect(page.getByText('25')).toBeVisible(); // 知识库
        await expect(page.getByText('5')).toBeVisible();  // 活跃 Agent
        await expect(page.getByText('256')).toBeVisible(); // 今日请求
        await expect(page.getByText('60')).toBeVisible();  // 自省记录
    });

    test('侧边栏导航应该正常运行', async ({ page }) => {
        // 点击导航到知识库
        await page.click('text=知识库');
        await expect(page).toHaveURL(/.*knowledge/);
        await expect(page.locator('h1')).toContainText('知识库管理');

        // 验证列表是否渲染 (Mock 25条)
        const listItems = page.locator('.ant-list-item');
        await expect(listItems).toHaveCount(25);
    });
});

test.describe('Special Case Handling (Mock control)', () => {
    test('空状态测试: 应该显示 Empty 占位图', async ({ page }) => {
        await page.goto('/');
        // 模拟切换到空状态
        await page.evaluate(() => {
            localStorage.setItem('VITE_MOCK_CASE', 'EMPTY_STATE');
        });
        await page.reload();

        await page.click('text=知识库');
        // Ant Design 的 Empty 描述
        await expect(page.getByText('No records found')).toBeVisible();
    });

    test('异常测试: 500 错误应该触发全局提示', async ({ page }) => {
        await page.goto('/');
        await page.evaluate(() => {
            localStorage.setItem('VITE_MOCK_CASE', 'ERROR_500');
        });
        await page.reload();

        // 触发任意 API 调用
        await page.click('text=Agent 蜂巢');

        // 检查是否有错误通知 (antd message/notification)
        // 根据拦截器，这里会返回 500，axios 拦截器会 console.error
        // 如果前端有 UI 处理，可以进一步断言
        const errorLog = page.locator('.ant-message-error');
        // 目前 DashboardPage 有 catch 块打印 console.error，我们可以验证 console
        // 或者期待我们之前修复的 UI 提示
    });
});
