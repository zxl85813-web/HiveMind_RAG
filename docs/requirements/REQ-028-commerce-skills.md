# REQ-028: Smart Commerce (Order & Logistics) Skills

| 字段 | 值 |
|------|------|
| **编号** | REQ-028 |
| **标题** | 智能电商查询技能 (订单与物流) |
| **来源** | 用户对话 (2026-04-19) |
| **优先级** | 高 |
| **状态** | 🟡 设计中 |
| **关联设计** | DES-028 (待创建) |
| **关联代码** | `mcp-servers/commerce-server/`, `skills/order-management/`, `skills/logistics-tracking/` |

## 需求描述
为 HiveMind 系统（目前嵌入在 RAGFlow 产品中）提供独立的订单和物流查询功能。该功能应通过 MCP (Model Context Protocol) 工具集和两个高层 Skill 实现，以便 AI 能够根据用户意图自动执行查询任务。

## 详细要求 (基于业务方案 PDF)
1. **意图识别 (Intent Recognition)**:
   - 01: 订单信息查询 (Order Details)
   - 02: 物流进度查询 (Shipment Tracking)
   - 03: 订单取消 (Order Cancellation)
   - 04: 地址变更 (Address Change Request)
   - 支持多意图组合（如：查询订单并确认地址）。

2. **单号识别规则 (ID Formats)**:
   - **官网订单**: `EFXX-数字` / `#12345` (示例: EFUS-121453, #45446)
   - **亚马逊订单**: `3-7-7` 格式 (示例: 112-9710404-9205034)
   - **物流单号**: 标准物流号 (如 SF, JD) 或 17track 兼容格式。

3. **业务逻辑流 (Business Protocol)**:
   - **登录状态校验**: 对接传参 `is_logged_in`。
     - 若未登录且涉及敏感操作（如查详情、改地址），需根据单号引导登录（官网发起弹窗）。
   - **优先级处理**: 若用户同时提供多个参数，优先使用订单号。
   - **多轮追问**: 若单号不全且意图明确，需追问至多3次，若仍无则引导至人工客服。

4. **MCP 服务接口**:
   - `crm_get_order(order_id, is_logged_in)`: 对接 CRM/OMS，返回订单详情、设备权益、收货人等。
   - `logistics_track_17track(tracking_no)`: 对接 17track 接口，返回最新轨迹、承运商、派送状态。
   - `oms_cancel_order(order_id)`: 执行订单取消申请。
   - `oms_update_address(order_id, new_address)`: 执行地址变更。

## 验收标准
- [ ] AI 能识别 PDF 中定义的 4 种核心意图。
- [ ] AI 能够校验单号格式（如符合 EFXX 正则）。
- [ ] 在未登录状态下，AI 会输出引导登录的特定预设语料。
- [ ] 合并处理订单+物流的复合查询。

## 变更记录
| 日期 | 变更 | 人员 |
|------|------|------|
| 2026-04-19 | 初始创建 | Antigravity |
