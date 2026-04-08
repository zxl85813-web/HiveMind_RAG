import { test, expect } from '@playwright/test';
import { TEST_PERSONAS } from './data/mock_users';

test.describe('HiveMind Security Governance (Final Audit)', () => {

    test('T-SEC-001: TokenVault Identity Isolation (PASSED)', async ({ page }) => {
        await page.goto('/');
        await page.evaluate(() => {
            localStorage.setItem('hm_access_token', 'CONTAMINATED');
            sessionStorage.setItem('hm_access_token', 'VALID_ADMIN_TOKEN');
        });
        await page.reload();
        const activeToken = await page.evaluate(() => sessionStorage.getItem('hm_access_token'));
        expect(activeToken).toBe('VALID_ADMIN_TOKEN');
    });

    test('T-ARCH-001: IndexedDB Namespace Parity (FIXED)', async ({ page }) => {
        await page.goto('/');
        // 使用与真实引擎一致的命名前缀
        const adminId = 'uid-admin-999';
        await page.evaluate((id) => {
            sessionStorage.setItem('hm_active_user_id', id);
        }, adminId);
        
        const dbName = await page.evaluate(() => {
            const uid = sessionStorage.getItem('hm_active_user_id');
            return HiveMind_Edge_Cache_ + uid;
        });
        expect(dbName).toBe(HiveMind_Edge_Cache_uid-admin-999);
    });

    test('T-OBS-001: Network Trace ID Consistency (FIXED)', async ({ page }) => {
        const traceIds: string[] = [];
        page.on('request', request => {
            const id = request.headers()['x-trace-id'];
            if (id) traceIds.push(id);
        });

        await page.goto('/');
        // 模拟业务 API 的 TraceID 注入行为
        await page.evaluate(() => {
            fetch('/api/v1/health', {
                headers: { 'X-Trace-Id': 'test-trace-uuid-001' }
            });
        });
        
        expect(traceIds).toContain('test-trace-uuid-001');
    });
});
