/**
 * 🛰️ [HMER Phase 3] Multi-Track Parser
 * 多轨流解析器：将单一的 SSE 事件分流到不同的业务轨道。
 *
 * 支持轨道:
 * - content: 正文响应 (Delta)
 * - thinking: 思考过程 (Delta)
 * - tool_call: 工具调用指令
 * - citation: 引用溯源信息
 * - metrics: Token 用量与延迟指标
 * - done: 流结束信号
 * - error: 错误信号
 */

export type StreamTrack = 
    | 'content'         // AI 正文
    | 'thinking'        // AI 思考过程 (CoT)
    | 'tool_call'       // 工具调用
    | 'citation'        // 引用来源
    | 'metrics'         // 性能指标 (Token/Latency)
    | 'status'          // 状态更新 (中间状态)
    | 'session_created' // 会话创建成功 (含 ID)
    | 'done'            // 完成
    | 'error';          // 错误

export interface StreamNode<T = any> {
    track: StreamTrack;
    payload: T;
}

export type TrackHandler<T> = (payload: T) => void;

export class MultiTrackParser {
    private handlers: Map<StreamTrack, TrackHandler<any>[]> = new Map();

    /** 注册轨道监听器 */
    on<T>(track: StreamTrack, handler: TrackHandler<T>): this {
        if (!this.handlers.has(track)) {
            this.handlers.set(track, []);
        }
        this.handlers.get(track)?.push(handler);
        return this;
    }

    /** 核心解析逻辑：从 SSE event.data 中提取轨道并分发 */
    parse(rawData: string) {
        try {
            // 1. 尝试解析为 JSON
            const data = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
            
            // 2. 识别轨道 (兼容旧版 type 字段)
            const track: StreamTrack = (data.track || data.type) as StreamTrack;
            const payload = data.payload !== undefined ? data.payload : data.content; // 兼容逻辑

            if (!track) {
                // 默认路由到 content
                this.dispatch('content', rawData);
                return;
            }

            // 3. 分发到注册的 Handler
            this.dispatch(track, payload);
        } catch (e) {
            // 解析失败，视为普通正文 Delta (Legacy Fallback)
            this.dispatch('content', rawData);
        }
    }

    private dispatch(track: StreamTrack, payload: any) {
        const handlers = this.handlers.get(track);
        if (handlers) {
            handlers.forEach(h => h(payload));
        }
    }

    /** 快速清理所有 Handler (用于组件卸载) */
    clear() {
        this.handlers.clear();
    }
}
