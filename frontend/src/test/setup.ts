import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// 每次测试后清理 DOM
afterEach(() => {
    cleanup();
});

// Polyfill ResizeObserver for antd Table/Tabs/etc. in jsdom
global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};

// Suppress getComputedStyle errors from antd scrollbar measurement
const _getComputedStyle = window.getComputedStyle.bind(window);
window.getComputedStyle = (elt: Element, pseudoElt?: string | null) => {
    try {
        return _getComputedStyle(elt, pseudoElt ?? undefined);
    } catch {
        return {} as CSSStyleDeclaration;
    }
};

// Mock matchMedia for antd
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => { },
        removeListener: () => { },
        addEventListener: () => { },
        removeEventListener: () => { },
        dispatchEvent: () => { },
    }),
});
