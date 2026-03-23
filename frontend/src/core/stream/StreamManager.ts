import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { FetchEventSourceInit } from '@microsoft/fetch-event-source';
import { MultiTrackParser, type StreamTrack, type TrackHandler } from './MultiTrackParser';
import { llmMonitor } from './LLMHealthMonitor';
import { monitor } from '../MonitorService';

/**
 * 🛰️ [HMER Phase 3] Stream Manager
 * 弹性流管理器：支持断点续传、多轨解析与服务降级。
 */

export interface StreamOptions extends Omit<FetchEventSourceInit, 'onmessage' | 'onerror'> {
    url: string;
    body: any;                  // 原始请求 Body
    maxRetries?: number;        // 最大重试次数
    resumeFromIndex?: number;   // 显式传入恢复位置
}

/** 统一事件订阅器 */
export class StreamManager {
    private parser: MultiTrackParser = new MultiTrackParser();
    private abortController: AbortController | null = null;
    private retryCount = 0;
    private lastChunkIndex = -1;  // 当前接收到的最后一个分块 Index
    private isConnected = false;
    private startTime = 0;
    private hasSentTTFT = false;

    private options: StreamOptions;

    constructor(options: StreamOptions) {
        this.options = options;
        this.lastChunkIndex = options.resumeFromIndex ?? -1;
    }

    /** 订阅轨道事件 */
    on<T>(track: StreamTrack, handler: TrackHandler<T>): this {
        this.parser.on(track, handler);
        return this;
    }

    /** 建立 (或恢复) 连接 */
    async connect() {
        if (this.isConnected) this.disconnect();

        this.startTime = performance.now();
        this.hasSentTTFT = false;
        this.abortController = new AbortController();
        const { url, body, maxRetries = 5, ...fetchOptions } = this.options;

        // 🛰️ [断点续传协议]: 携带 last_chunk_index 告诉后端从哪继续
        const enhancedBody = {
            ...body,
            _resume_index: this.lastChunkIndex >= 0 ? this.lastChunkIndex : undefined
        };

        try {
            this.isConnected = true;
            await fetchEventSource(url, {
                ...fetchOptions,
                method: 'POST',
                headers: {
                    ...fetchOptions.headers,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(enhancedBody),
                signal: this.abortController.signal,

                onopen: async (response) => {
                    if (response.ok) {
                        llmMonitor.recordSuccess();
                        this.retryCount = 0; // 🛰️ [Fix]: 连接成功后重置重试计数器
                        console.log(`[StreamManager] SSE Connected (Resume Index: ${this.lastChunkIndex})`);
                    } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
                        // 客户端错误或鉴权失败，不重试
                        llmMonitor.recordError(response.status);
                        throw new Error(`SSE Connection Failed: ${response.status}`);
                    } else {
                        // 服务端错误或 429，尝试重试逻辑
                        llmMonitor.recordError(response.status);
                        // 🛰️ [Fix]: 必须抛出错误，否则 fetchEventSource 会认为连接成功而不会触发 onerror
                        throw new Error(`SSE Server Error: ${response.status}`);
                    }
                },

                onmessage: (event) => {
                    // 1. 获取消息流水号 (Chunk Index)
                    // 后端协议应返回: { track: "...", content: "...", _index: 123 }
                    try {
                        const data = JSON.parse(event.data);
                        if (data._index !== undefined) {
                            this.lastChunkIndex = Math.max(this.lastChunkIndex, data._index);
                        }
                    } catch { /* 如果不是 JSON，无法记录 Index */ }

                    // 2. 多轨分流解析
                    this.parser.parse(event.data);

                    // 🛰️ [Architecture-Check]: 遥测对账 - TTFT (Time To First Token)
                    if (!this.hasSentTTFT && event.data.includes('"track":"content"')) {
                        this.hasSentTTFT = true;
                        const ttft = Math.round(performance.now() - this.startTime);
                        console.log(`[Telemetry] Dispatching TTFT beacon: ${ttft}ms`);
                        monitor.dispatchBeacon('streaming_performance', { 
                            ttft_ms: ttft,
                            url: this.options.url,
                            resume_index: this.lastChunkIndex
                        });
                    }
                },

                onerror: (err) => {
                    this.isConnected = false;
                    this.retryCount++;
                    
                    // 🛰️ [Fix]: 在内部重试环路中，优先保证当前 Session 的重试尝试，直到耗尽 maxRetries
                    if (this.retryCount > maxRetries) {
                        console.error('[StreamManager] Max retries reached.');
                        throw err; // 到达极限，抛出给上层
                    }

                    // 3. 指数退避重试 (Exponential Backoff)
                    const delay = 1000 * Math.pow(2, this.retryCount);
                    console.warn(`[StreamManager] SSE Connection Lost. Retrying in ${delay}ms... (Count: ${this.retryCount})`);
                    
                    return delay;
                },

                onclose: () => {
                    this.isConnected = false;
                    console.log('[StreamManager] SSE closed.');
                }
            });
        } catch (e: any) {
            this.isConnected = false;
            if (this.abortController?.signal.aborted) {
                console.log('[StreamManager] SSE Swarm: Aborted by user.');
            } else {
                console.error('[StreamManager] SSE Swarm: Critical Error', e);
                // 🛰️ [Fix]: 触发错误轨道，避免 UI 永远卡在 loading 态。
                this.parser.parse(JSON.stringify({
                    track: 'error',
                    payload: e.message || 'Fatal Connection Error'
                }));
            }
        }
    }

    /** 主动断开当前连线器 */
    disconnect() {
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
        this.isConnected = false;
    }

    /** 彻底清理 (建议在组件卸载时调用) */
    destroy() {
        this.disconnect();
        this.parser.clear();
    }
}
