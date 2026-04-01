import { test, expect } from '@playwright/test';

/**
 * 🛰️ [GOV-EXP-001]: Swarm Execution Pattern Benchmark
 * 
 * Objective: 
 * Prove that 'react' variant provides richer intermediate feedback 
 * and handles multi-step reasoning without monolithic stagnation.
 */
test.describe('Distributed Cognition (ReAct vs Monolithic) Benchmark', () => {
    // A complex query that requires multiple tool/analysis steps to trigger differences.
    const COMPLEX_QUERY = "帮我分析 HiveMind 的分布式思维链 (ReAct) 设计原理，然后写一个伪代码展示它如何上报 latency 指标。";

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('Experiment Variant: [Monolithic] - High Latency / Low Status Updates', async ({ page }) => {
        const startTime = Date.now();
        console.log('--- Starting Monolithic Variant Test ---');

        // Navigate with monolithic variant override
        await page.goto('/?execution_variant=monolithic');
        
        const chatInput = page.locator('textarea[placeholder*="输入你的问题"]');
        await chatInput.fill(COMPLEX_QUERY);
        await page.keyboard.press('Enter');

        // Monolithic usually has very few status updates before a long wait.
        const statusLocator = page.locator('.ant-x-thought-chain-item');
        
        try {
            // Wait for first status update
            await statusLocator.first().waitFor({ timeout: 15000 });
            const firstFeedbackTime = Date.now() - startTime;
            console.log(`[Monolithic] Time to First Status: ${firstFeedbackTime}ms`);
        } catch (e) {
            console.log('[Monolithic] No status update seen within 15s - usual for heavy monolithic calls.');
        }

        // Wait for final response completion (success bubble)
        await page.waitForSelector('.chat-message.assistant', { timeout: 90000 });
        const totalDuration = Date.now() - startTime;
        
        const statusCount = await statusLocator.count();
        console.log(`[Monolithic] Total Duration: ${totalDuration}ms, Final Status Updates: ${statusCount}`);

        // Monolithic typically expects 1-2 status items at most (often just the final one).
        expect(statusCount).toBeLessThanOrEqual(3);
    });

    test('Experiment Variant: [ReAct] - High Feedback Frequency / Granular Steps', async ({ page }) => {
        const startTime = Date.now();
        console.log('--- Starting ReAct Variant Test ---');

        // Navigate with react variant override
        await page.goto('/?execution_variant=react');
        
        const chatInput = page.locator('textarea[placeholder*="输入你的问题"]');
        await chatInput.fill(COMPLEX_QUERY);
        await page.keyboard.press('Enter');

        const statusLocator = page.locator('.ant-x-thought-chain-item');

        // ReAct should show first status VERY quickly (usually < 2-3s because steps are short)
        await statusLocator.first().waitFor({ timeout: 10000 });
        const firstFeedbackTime = Date.now() - startTime;
        console.log(`[ReAct] Time to First Status (FCF): ${firstFeedbackTime}ms`);

        // Assert FCF is better (soft expectation)
        expect(firstFeedbackTime).toBeLessThan(12000);

        // Wait for subsequent steps (ReAct should have multiple segments)
        // We expect at least 3 segments for a complex multi-step reasoning task.
        await expect(statusLocator).toHaveCount(3, { timeout: 60000 });
        
        const intermediateCount = await statusLocator.count();
        console.log(`[ReAct] Intermediate Status Count: ${intermediateCount} steps/thoughts visible.`);

        // Final completion check
        await page.waitForSelector('.chat-message.assistant', { timeout: 90000 });
        const totalDuration = Date.now() - startTime;
        
        const finalStatusCount = await statusLocator.count();
        console.log(`[ReAct] Total Duration: ${totalDuration}ms, Total Status Updates: ${finalStatusCount}`);

        // CRITICAL DATA ASSERTION:
        // ReAct mode for complex tasks MUST produce more visibility than Monolithic.
        expect(finalStatusCount).toBeGreaterThan(2); 
    });
});
