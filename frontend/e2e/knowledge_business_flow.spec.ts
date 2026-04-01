import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/**
 * 🕸️ [REQ-KB-FLOW]: 知识库业务全链路系统测试 (Playwright E2E)
 * 
 * 包含阶段: 登录 -> 常规数据准备 -> 录入知识 -> 质量审核 -> 上架检索验证
 * 每个阶段设置了明确的 Checkpoint (数据与 UI 状态断言)。
 */
test.describe('HiveMind 全链路业务场景测试 (System-Level)', () => {
    const testId = `E2E_${Date.now().toString().slice(-4)}`;
    const kbName = `项目研发规范库_${testId}`;
    const testFileName = `e2e_spec_${testId}.txt`;
    const testContent = `
        项目研发规范 (Revision ${testId})
        1. 核心代号: HVM-ALPHA-99
        2. 开发语言: TypeScript + Python
        3. 架构模式: Swarm Intelligence
        本文件由全链路自动化测试脚本生成。
    `;

    test.beforeAll(async () => {
        // 准备初始数据文件
        const filePath = path.join(process.cwd(), 'e2e', testFileName);
        fs.writeFileSync(filePath, testContent);
    });

    test('应完成从录入到检索的闭环流程', async ({ page }) => {
        // [Checkpoint 0: 登录授权]
        // 由于项目在开发环境默认 Mock Auth，我们确认是否能看到 Dashboard
        await page.goto('/');
        await expect(page.locator('h1, h2:has-text("HiveMind Intelligence")')).toBeVisible();
        console.log('✅ C0: 授权成功，进入仪表盘');

        // [Checkpoint 1: 知识库初始录入]
        await page.goto('/knowledge');
        await expect(page.locator('button:has-text("新建")')).toBeVisible();

        await page.click('button:has-text("新建")');
        await page.fill('input[placeholder*="名称"]', kbName);
        await page.fill('textarea[placeholder*="描述"]', '自动化全链路测试生成的知识库');
        await page.click('.ant-modal-footer button:has-text("确 认")');
        
        // 验证中间数据：知识库出现在列表
        await expect(page.locator(`text=${kbName}`)).toBeVisible({ timeout: 5000 });
        console.log('✅ C1: 知识库容器创建成功');

        // [Checkpoint 2: 知识录入与上传]
        await page.click(`text=${kbName}`);
        await expect(page.locator('.ant-drawer-title:has-text("' + kbName + '")')).toBeVisible();

        // 查找隐藏的 input 元素进行文件上传
        const fileChooserPromise = page.waitForEvent('filechooser');
        await page.click('.ant-upload-drag');
        const fileChooser = await fileChooserPromise;
        await fileChooser.setFiles(path.join(process.cwd(), 'e2e', testFileName));

        // 验证中间数据：文件列表出现且状态为 PENDING_REVIEW
        // 我们需要等待 API 返回并渲染
        const docRow = page.locator(`.ant-table-row:has-text("${testFileName}")`);
        await expect(docRow).toBeVisible({ timeout: 15000 });
        
        // 检查状态标签
        await expect(docRow.locator('.ant-tag:has-text("PENDING_REVIEW")')).toBeVisible({ timeout: 10000 });
        console.log('✅ C2: 文档上传成功且进入待审核队列');

        // [Checkpoint 3: 质量审核与入库/上架]
        await page.goto('/audit');
        await expect(page.locator('h3:has-text("数据质量审核控制台")')).toBeVisible();

        // 在审核队列中定位我们的文件
        // 注意：由于是系统级测试，可能有其他干扰数据，我们根据 docId 或文件名过滤（如果前端支持）
        // 这里假设最新的一条就是刚才上传的（按时间倒序）
        const reviewRow = page.locator(`.ant-table-row:has-text("${testFileName}"), .ant-table-row:has-text("${testId}")`).first();
        await expect(reviewRow).toBeVisible();
        
        // 执行通过操作
        await reviewRow.locator('button:has-text("通过")').click();
        await expect(page.locator('text=审核已通过')).toBeVisible();
        console.log('✅ C3: 文档质量审核通过');

        // [Checkpoint 4: 最终上架状态与检索能力验证]
        // 返回知识库详情，确认状态变为 INDEXED
        await page.goto('/knowledge');
        await page.click(`text=${kbName}`);
        
        const finalDocRow = page.locator(`.ant-table-row:has-text("${testFileName}")`);
        await expect(finalDocRow.locator('.ant-tag:has-text("INDEXED")')).toBeVisible({ timeout: 15000 });
        console.log('✅ C4: 文档通过审核并完成索引入库');

        // 执行检索测试
        await page.click('div[role="tab"]:has-text("检索测试")');
        await page.fill('input[placeholder*="输入问题"]', 'HVM-ALPHA-99');
        await page.click('button:has-text("搜索")');

        // 验证最终数据：内容被成功召回
        await expect(page.locator('.ant-list-item:has-text("项目研发规范")')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('.ant-list-item:has-text("Swarm Intelligence")')).toBeVisible();
        console.log('✅ C5: 全链路业务闭环检索验证成功');
    });

    test.afterAll(async () => {
        // 清理本地文件
        const filePath = path.join(process.cwd(), 'e2e', testFileName);
        if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }
    });
});
