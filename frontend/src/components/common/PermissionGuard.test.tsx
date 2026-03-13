import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PermissionButton, PermissionGuard } from './PermissionGuard';
import { useAuthStore } from '../../stores/authStore';

vi.mock('../../stores/authStore', () => ({
    useAuthStore: vi.fn(),
}));

describe('Permission Controls', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('hides permission button when unauthorized in hide mode', () => {
        vi.mocked(useAuthStore).mockImplementation((selector: any) => selector({ hasAccess: () => false }));

        const { container } = render(
            <PermissionButton access={{ anyPermissions: ['settings:manage'] }}>
                Save
            </PermissionButton>,
        );

        expect(container).toBeEmptyDOMElement();
    });

    it('disables permission button when unauthorized in disable mode', () => {
        vi.mocked(useAuthStore).mockImplementation((selector: any) => selector({ hasAccess: () => false }));

        render(
            <PermissionButton access={{ anyPermissions: ['settings:manage'] }} mode="disable">
                Save
            </PermissionButton>,
        );

        expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    });

    it('renders enabled permission button when authorized', () => {
        vi.mocked(useAuthStore).mockImplementation((selector: any) => selector({ hasAccess: () => true }));

        render(
            <PermissionButton access={{ anyPermissions: ['settings:manage'] }}>
                Save
            </PermissionButton>,
        );

        expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled();
    });

    it('hides guarded content when unauthorized in hide mode', () => {
        vi.mocked(useAuthStore).mockImplementation((selector: any) => selector({ hasAccess: () => false }));

        const { queryByText } = render(
            <PermissionGuard access={{ anyPermissions: ['security:manage'] }}>
                <div>Sensitive Panel</div>
            </PermissionGuard>,
        );

        expect(queryByText('Sensitive Panel')).not.toBeInTheDocument();
    });

    it('renders guarded content when authorized', () => {
        vi.mocked(useAuthStore).mockImplementation((selector: any) => selector({ hasAccess: () => true }));

        render(
            <PermissionGuard access={{ anyPermissions: ['security:manage'] }}>
                <div>Sensitive Panel</div>
            </PermissionGuard>,
        );

        expect(screen.getByText('Sensitive Panel')).toBeInTheDocument();
    });
});