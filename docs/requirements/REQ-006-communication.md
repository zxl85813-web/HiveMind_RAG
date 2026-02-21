# REQ-006: 混合通信 (SSE + WebSocket)

| 字段 | 值 |
|------|------|
| **编号** | REQ-006 |
| **标题** | SSE + WebSocket 混合通信架构 |
| **来源** | 用户对话 (2026-02-15) |
| **优先级** | 高 |
| **状态** | 🟡 框架已搭建，待实现 |
| **关联代码** | `backend/app/api/routes/chat.py`, `backend/app/api/routes/websocket.py`, `backend/app/services/ws_manager.py` |

## 需求描述

基础问答使用 SSE 流式输出。系统主动推送（Agent 状态、通知、建议、学习动态等）通过 WebSocket 持久连接。

## 验收标准

- [ ] SSE 流式输出正常工作
- [ ] WebSocket 连接稳定、支持重连
- [ ] 支持多种服务端推送事件类型
- [ ] 支持客户端取消正在生成的回答

## 变更记录

| 日期 | 变更 | 人员 |
|------|------|------|
| 2026-02-15 | 初始创建 | AI |
