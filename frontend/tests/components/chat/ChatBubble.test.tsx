import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ChatBubble } from '@/components/chat/ChatBubble';
import { describe, it, expect, vi } from 'vitest';

describe('ChatBubble Component (Path Normalization)', () => {
    const mockMessage = {
        id: '1',
        role: 'swarm' as const,
        content: 'Test content',
        thoughts: ['Thinking test']
    };

    it('should be importable from the standard chat directory', () => {
        render(<ChatBubble message={mockMessage} />);
        expect(screen.getByText('Test content')).toBeInTheDocument();
    });
});
