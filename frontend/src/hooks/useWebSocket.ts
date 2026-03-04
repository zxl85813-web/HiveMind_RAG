import { useState, useEffect, useCallback, useRef } from 'react';

interface UseWebSocketOptions {
    url: string;
    onMessage?: (event: MessageEvent) => void;
    onOpen?: (event: Event) => void;
    onClose?: (event: CloseEvent) => void;
    onError?: (event: Event) => void;
    reconnectInterval?: number;
    reconnectAttempts?: number;
    autoConnect?: boolean;
}

export function useWebSocket({
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 3000,
    reconnectAttempts = 5,
    autoConnect = false
}: UseWebSocketOptions) {
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<Event | null>(null);
    const attemptsRef = useRef(0);
    const wsRef = useRef<WebSocket | null>(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        try {
            const wsUrl = url.startsWith('http') ? url.replace('http', 'ws') : url;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = (event) => {
                setIsConnected(true);
                setError(null);
                attemptsRef.current = 0;
                setSocket(ws);
                onOpen?.(event);
            };

            ws.onmessage = (event) => {
                onMessage?.(event);
            };

            ws.onclose = (event) => {
                setIsConnected(false);
                setSocket(null);
                onClose?.(event);

                // Auto-reconnect
                if (attemptsRef.current < reconnectAttempts && event.code !== 1000) {
                    setTimeout(() => {
                        attemptsRef.current += 1;
                        connect();
                    }, reconnectInterval);
                }
            };

            ws.onerror = (event) => {
                setError(event);
                onError?.(event);
            };
        } catch (err: any) {
            console.error("WebSocket connection error:", err);
            setError(err);
        }
    }, [url, onMessage, onOpen, onClose, onError, reconnectAttempts, reconnectInterval]);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close(1000, 'User initiated disconnect');
            wsRef.current = null;
        }
    }, []);

    const sendMessage = useCallback((data: string | object) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            const message = typeof data === 'string' ? data : JSON.stringify(data);
            wsRef.current.send(message);
        } else {
            console.warn('WebSocket is not connected');
        }
    }, []);

    useEffect(() => {
        if (autoConnect) {
            connect();
        }
        return () => {
            disconnect();
        };
    }, [autoConnect, connect, disconnect]);

    return {
        isConnected,
        error,
        sendMessage,
        connect,
        disconnect,
        socket
    };
}
