---
name: logistics-tracking
description: "处理物流进度查询 (意图 02)。对接 17track 实时查询接口，支持官网订单号自动关联查询或直接使用运单号。"
---

# Logistics Tracking Skill (Intent 02)

## ⚡ 快速参考 (Quick Reference)

| 场景 | 核心动作 | 对应工具 |
|------|----------|----------|
| 通过单号查进度 | 调用 17track | `logistics_track_17track(tracking_no)` |
| 通过订单查进度 | 联动查询 | 先调用 `crm_get_order` 获取跟踪号，再调用 17track |

## 📋 完整规程 (Full Protocol)

### 第一步：识别进线意向
当用户输入"我的东西到哪了"、"快递怎么还没更新"时，进入此流程。

### 第二步：智能查询链路
1.  **优先级**: 若用户同时提供了订单号和物流单号，优先使用物流单号。
2.  **自动关联**: 若仅提供订单号，调用 `crm_get_order`。
    - 若订单状态为 `Pending` (未发货)，直接回复："该订单目前还在备货中，尚未产生运单号。"
    - 若已发货，提取 `tracking_no` 并自动执行 `logistics_track_17track`。

### 第三步：人性化回复架构
1.  **首句**: 加粗显示当前位置。
2.  **预计**: 基于最新记录判断（如"正在派送" -> "今日有望送达"）。
3.  **轨迹**: 仅展示最近3条轨迹信息，避免信息过载。

## 🔒 强制准则 (Critical Rules)

| 规则 | 说明 |
|------|------|
| 数据同步 | 明确告知用户："物流信息由 17track 提供，可能存在 1-2 小时同步延迟。" |
| 匹配性校验 | 若用户提供的物流号与订单号在 CRM 中不匹配，提示用户核对。 |
| 外部链接 | 在回复末尾引导用户："您可以访问 17track.net 输入单号查看完整的国际运输明细。" |

## 🗂️ 资源
- **MCP Tool**: `logistics_track_17track`
- **OCR Reference**: PDF Page 6 (17track integration detail)
