import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';

// Mock the MonitorService
vi.mock('../../../core/MonitorService', () => ({
    monitor: {
        reportError: vi.fn(),
    },
}));

const ThrowError = () => {
    throw new Error('Test Error');
};

describe('ErrorBoundary Severity Test', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Prevent React from logging the error to console during test
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    it('should report error with severity "critical" when a component crashes', async () => {
        const { monitor } = await import('../../../core/MonitorService');

        
        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        // componentDidCatch is async because of the dynamic import
        // We wait for the mock to be called
        await vi.waitFor(() => {
            expect(monitor.reportError).toHaveBeenCalled();
        });

        const callArgs = vi.mocked(monitor.reportError).mock.calls[0];
        const metadata = callArgs[1] as any;

        // Check if severity is 'critical'
        // Currently it should FAIL because ErrorBoundary.tsx doesn't pass severity
        expect(metadata).toHaveProperty('severity', 'critical');
    });
});
