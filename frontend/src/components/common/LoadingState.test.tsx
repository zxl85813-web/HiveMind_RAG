import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LoadingState } from './LoadingState';
import React from 'react';

describe('LoadingState Component', () => {
    it('renders with default tip "加载中..."', () => {
        render(<LoadingState />);
        expect(screen.getByText('加载中...')).toBeInTheDocument();
    });

    it('renders with custom tip', () => {
        const customTip = '数据加载中，请稍候';
        render(<LoadingState tip={customTip} />);
        expect(screen.getByText(customTip)).toBeInTheDocument();
    });

    it('renders in fullScreen mode', () => {
        const { container } = render(<LoadingState fullScreen={true} />);
        const div = container.firstChild as HTMLElement;
        expect(div).toHaveStyle({
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
        });
    });
});
