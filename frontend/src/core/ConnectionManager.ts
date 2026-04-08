import type { StreamManager } from './stream/StreamManager';

/**
 * 🛰️ [Architecture-Gate]: Connection Manager
 * 集中治理长连接 (SSE, WebSocket) 的生命周期。
 * 尤其在用户切换、Token 失效时，确保全量连接物理断开，防止数据泄露。
 */
class ConnectionManager {
    private sseConnections: Set<StreamManager> = new Set();
    private wsConnections: Set<WebSocket> = new Set();

    /** 注册 SSE 连接 */
    registerSSE(stream: StreamManager) {
        this.sseConnections.add(stream);
    }

    /** 注销 SSE 连接 */
    unregisterSSE(stream: StreamManager) {
        this.sseConnections.delete(stream);
    }

    /** 注册 WebSocket 连接 */
    registerWS(ws: WebSocket) {
        this.wsConnections.add(ws);
    }

    /** 注销 WebSocket 连接 */
    unregisterWS(ws: WebSocket) {
        this.wsConnections.delete(ws);
    }

    /** 
     * [Security]: 熔断所有长连接 
     * 用户注销、身份切换或系统挂起时强制调用。
     */
    abortAll() {
        console.warn('🛰️ [ConnectionManager] Aborting all active long-connections for security.');
        
        // 1. 断开并销毁所有 SSE
        this.sseConnections.forEach(stream => {
            try {
                stream.destroy();
            } catch (e) {
                console.error('Failed to destroy SSE during abortAll', e);
            }
        });
        this.sseConnections.clear();

        // 2. 关闭所有 WebSocket
        this.wsConnections.forEach(ws => {
            try {
                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close(1000, 'System manual abort (Auth Switch)');
                }
            } catch (e) {
                console.error('Failed to close WS during abortAll', e);
            }
        });
        this.wsConnections.clear();
    }
}

export const connectionManager = new ConnectionManager();
