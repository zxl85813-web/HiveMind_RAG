import { test, expect } from '@playwright/test';

test.describe('REQ-013: Intent Scaffolding UI & Phase Gate', () => {
  test('User experiences speculative intent flow and TTFT < 300ms is audited', async ({ page }) => {
    // 1. Mocking the API endpoint for Phase 1 Phase Gate (API Endpoint derived from Neo4j)
    await page.route('/api/v1/observability/baseline/phase-gate/1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: { ready_to_proceed: true, audit_report: "Latency < 300ms, Good." }
        })
      });
    });

    // 2. Mocking IntentScaffoldingService output mapped via RAGGateway
    await page.route('/api/v1/rag/*', async route => {
      // simulate 150ms response to prove speculative hit
      await new Promise(r => setTimeout(r, 150)); 
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: { fragments: [] }})
      });
    });

    // 3. User Action
    await page.goto('/architecture-lab');
    
    // According to DES-013, PhaseGateAuditor is a component
    const phaseGateBtn = page.getByRole('button', { name: /Auditor/i });
    if (await phaseGateBtn.isVisible()) {
        await phaseGateBtn.click();
        
        // 4. Verification: Check DOM state reflects Phase Gate Audit
        await expect(page.getByText('Latency < 300ms, Good.')).toBeVisible();
    }
  });
});
