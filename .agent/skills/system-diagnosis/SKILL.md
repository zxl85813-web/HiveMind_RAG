---
name: system-diagnosis
description: 全栈故障诊断与日志溯源技能 — 允许 AI 自动串联前后端日志并定位 Bug 根因。
version: 1.0.0
---

# 🕵️ System Diagnosis Skill

本技能为 Antigravity (IDE Agent) 提供了一套标准的“全栈查错”流程，利用已打通的前后端统一日志体系，实现分钟级的故障定位。

## 🛠️ 核心能力

1.  **全链路溯源 (Trace Reconstruction)**: 利用 `trace_id` 将孤立的前后端日志碎片重建成逻辑严密的“意识流”。
2.  **错误热点分析 (Error Hotspot)**: 快速扫描 `logs/` 下的 JSON 日志，识别发生频率最高的异常。
3.  **状态机对齐 (State Alignment)**: 检查前端发送的 Request 是否与后端接收到的 Payload 以及数据库产生的 Side-effect 完全对齐。

## 📖 使用指南 (How to use)

### 1. 执行全链路分析
当你需要了解某个特定请求为什么失败时，请执行：
```powershell
python backend/scripts/trace_analyzer.py --id <trace_id>
```
*提示: 可以在 `frontend/src/services/loggingService.ts` 中找到 Trace ID，或者在 API 响应头 `X-Trace-Id` 中获取。*

### 2. 扫描最近的错误
如果你想知道系统刚才报了什么错，可以直接 grep 日志目录：
```powershell
# Windows
Select-String -Path "backend/logs/*.log" -Pattern '"level":"ERROR"' | Select-Object -First 10
```

### 3. 跨端检查清单
诊断时请检查以下三个维度：
- **FE 层**: 检查 `console-error` 标签，确定是否为前端交互或渲染逻辑错误。
- **Transport 层**: 检查 `TraceMiddleware` 生成的日志，确认请求头、路径、耗时是否正常。
- **BE 层**: 检查 `hivemind_*.log` 中的 `exception` 字段，获取 Python 堆栈信息。

## 🎯 触发场景
- 当用户说 "帮我查一下为什么刚才报错了"
- 当出现 "网络连接失败" 或 "接口 500" 时
- 当需要验证全栈执行流的一致性时
