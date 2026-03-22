import { useState, useCallback } from 'react';
import { chatApi } from '../services/chatApi';
import type { ChatMessage } from '../services/chatApi';
import { baseline } from '../core/BaselineProbe';

export interface UseChatOptions {
    initialMessages?: ChatMessage[];
    conversationId?: string | null;
    knowledgeBaseIds?: string[];
    contextPage?: string;
    onStatus?: (status: string) => void;
    onTagsDetected?: (tags: string[]) => void;
    onSessionCreated?: (id: string, title: string) => void;
    onFinish?: () => void;
    onError?: (err: unknown) => void;
}

export function useChat(options: UseChatOptions = {}) {
    const {
        initialMessages = [],
        conversationId,
        knowledgeBaseIds = [],
        contextPage,
        onStatus,
        onTagsDetected,
        onSessionCreated,
        onFinish,
        onError
    } = options;

    const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [controller, setController] = useState<AbortController | null>(null);

    const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setInput(e.target.value);
    }, []);

    const sendMessage = useCallback(async (text: string) => {
        if (!text.trim()) return;

        const userMsg: ChatMessage = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: text,
            created_at: new Date().toISOString(),
            metadata: contextPage ? { context_page: contextPage } : undefined,
        };

        const aiMsg: ChatMessage = {
            id: `ai-${Date.now()}`,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
            metadata: { statuses: [] }
        };

        setMessages(prev => [...prev, userMsg, aiMsg]);
        setInput('');
        setIsLoading(true);
        baseline.mark(`chat-start-${userMsg.id}`);

        const newController = new AbortController();
        setController(newController);

        let fullContent = '';
        let fullThinking = '';
        const statuses: string[] = [];

        const streamManager = chatApi.getResilientStream({
            message: text,
            conversationId,
            knowledgeBaseIds,
        });

        streamManager
            .on('content', (delta: string) => {
                if (fullContent === '') {
                    baseline.mark(`chat-first-delta-${userMsg.id}`);
                    baseline.measure(
                        'TTFT (Baseline)',
                        `chat-start-${userMsg.id}`,
                        `chat-first-delta-${userMsg.id}`
                    );
                }
                fullContent += delta;
                setMessages(prev => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last.id === aiMsg.id) {
                        last.content = fullContent;
                    }
                    return next;
                });
            })
            .on('thinking', (delta: string) => {
                fullThinking += delta;
                setMessages(prev => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last.id === aiMsg.id) {
                        last.metadata = { ...last.metadata, thinking: fullThinking };
                    }
                    return next;
                });
            })
            .on('status', (status: string) => {
                statuses.push(status);
                setMessages(prev => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last.id === aiMsg.id) {
                        last.metadata = { ...last.metadata, statuses: [...statuses] };
                    }
                    return next;
                });

                onStatus?.(status);

                const match = status.match(/Tags: \[(.*?)\]/);
                if (match && match[1]) {
                    const tags = match[1].split(',').map(t => t.trim());
                    onTagsDetected?.(tags);
                }
            })
            .on('citation', (citations: any) => {
                setMessages(prev => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last.id === aiMsg.id) {
                        last.metadata = { ...last.metadata, citations };
                    }
                    return next;
                });
            })
            .on('done', () => {
                setIsLoading(false);
                onFinish?.();
            })
            .on('error', (err: any) => {
                console.error('Chat error:', err);
                const errorText = `\n[系统错误: ${err.message || '无法连接到 AI 服务'}]`;
                setMessages(prev => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last.id === aiMsg.id) {
                        last.content += errorText;
                    }
                    return next;
                });
                setIsLoading(false);
                onError?.(err);
            });

        // 将 manager 存入 state 以便 stop 控制
        setController({ abort: () => streamManager.disconnect() } as any);

        await streamManager.connect();
    }, [conversationId, knowledgeBaseIds, contextPage, onStatus, onTagsDetected, onSessionCreated, onFinish, onError]);

    const stop = useCallback(() => {
        if (controller) {
            (controller as any).abort();
            setController(null);
            setIsLoading(false);
        }
    }, [controller]);

    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    return {
        messages,
        setMessages,
        input,
        setInput,
        handleInputChange,
        sendMessage,
        isLoading,
        stop,
        clearMessages
    };
}
