import { useState, useRef, useCallback, useEffect } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { FetchEventSourceInit } from '@microsoft/fetch-event-source';

interface UseSSEOptions extends Omit<FetchEventSourceInit, 'onmessage' | 'onerror' | 'onopen'> {
    url: string;
    onMessage?: (data: any, event: string) => void;
    onError?: (error: any) => void;
    onOpen?: () => void;
    autoConnect?: boolean;
}

export function useSSE(options: UseSSEOptions) {
    const { url, onMessage, onError, onOpen, autoConnect = false, ...fetchOptions } = options;
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const connect = useCallback(async (body?: any) => {
        disconnect(); // Disconnect previous connection if any
        setError(null);

        const controller = new AbortController();
        abortControllerRef.current = controller;

        const connectOptions: FetchEventSourceInit = {
            ...fetchOptions,
            signal: controller.signal,
            async onopen(response) {
                if (response.ok) {
                    setIsConnected(true);
                    onOpen?.();
                } else {
                    const err = new Error(`Failed to connect SSE. Status: ${response.status}`);
                    setError(err);
                    throw err; // Stop retrying
                }
            },
            onmessage(event) {
                try {
                    let parsedData = event.data;
                    try {
                        parsedData = JSON.parse(event.data);
                    } catch {
                        // Keep as string if not JSON
                    }
                    onMessage?.(parsedData, event.event);
                } catch (e) {
                    console.error('Error handling SSE message:', e);
                }
            },
            onerror(err) {
                setError(err);
                onError?.(err);
                setIsConnected(false);
                throw err; // Prevent default retry on serious error depending on requirements
            },
            onclose() {
                setIsConnected(false);
            }
        };

        if (body) {
            connectOptions.method = connectOptions.method || 'POST';
            connectOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
        }

        try {
            await fetchEventSource(url, connectOptions);
        } catch (err) {
            setIsConnected(false);
            if (err instanceof Error && err.name !== 'AbortError') {
                setError(err);
            }
        }
    }, [url, onMessage, onError, onOpen, fetchOptions]);

    const disconnect = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        setIsConnected(false);
    }, []);

    useEffect(() => {
        if (autoConnect) {
            connect();
        }
        return () => disconnect();
    }, [autoConnect, connect, disconnect]);

    return {
        connect,
        disconnect,
        isConnected,
        error
    };
}
