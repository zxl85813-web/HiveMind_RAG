import random
import re
from datetime import datetime, timedelta
from fastmcp import FastMCP

# Initialize FastMCP server
# In a real scenario, this would connect to CRM, OMS, and 17track APIs
mcp = FastMCP("CommercePlatform")

# --- Regex for ID validation ---
RE_OFFICIAL_ORDER = re.compile(r'^EF[A-Z]{2}-\d{6}$|^#\d{5}$', re.IGNORECASE)
RE_AMAZON_ORDER = re.compile(r'^\d{3}-\d{7}-\d{7}$', re.IGNORECASE)

# --- Mock Databases ---
MOCK_CRM = {
    "EFUS-121453": {
        "status": "shipped",
        "items": [{"sku": "P001", "name": "EcoFlow DELTA 2", "qty": 1}],
        "amount": 5999.00,
        "customer": "Cherry Zhang",
        "address": "深圳市南山区科技园",
        "tracking_no": "SF178822930",
        "requires_login": True
    },
    "112-9710404-9205034": {
        "status": "pending",
        "items": [{"sku": "P002", "name": "Portable Solar Panel", "qty": 2}],
        "amount": 2899.00,
        "customer": "Taven Huang",
        "address": "Los Angeles, CA",
        "tracking_no": None,
        "requires_login": False
    }
}

MOCK_17TRACK = {
    "SF178822930": [
        {"time": "2026-04-18 10:00", "status": "In Transit", "desc": "Arrived at Shenzhen Distribution Center"},
        {"time": "2026-04-19 08:30", "status": "Delivering", "desc": "Out for delivery by Courier Wang"}
    ]
}

@mcp.tool()
def crm_get_order(order_id: str, is_logged_in: bool = False) -> str:
    """
    Get order details from CRM/OMS.
    If is_logged_in is False and order requires login, sensitive info will be redacted.
    """
    oid = order_id.upper()
    order = MOCK_CRM.get(oid)
    if not order:
        return f"ERROR_001: 未找到订单 {order_id} 记录，请核对后重试。"

    if order["requires_login"] and not is_logged_in:
        return (
            f"### 订单已找到: {oid}\n"
            f"⚠️ **安全提示**: 该订单包含敏感私密信息。为了保护您的隐私，请先登录您的官网账户。\n"
            f"请点击页面右上角的【登录】按钮，登录后我将为您展示详细清单。"
        )

    res = f"### 订单详情 ({oid})\n"
    res += f"- **用户**: {order['customer']}\n"
    res += f"- **状态**: {order['status']}\n"
    res += f"- **金额**: ￥{order['amount']:.2f}\n"
    res += f"- **寄送地址**: {order['address']}\n"
    res += "**购买明细**:\n"
    for item in order['items']:
        res += f"  - {item['name']} (SKU: {item['sku']}) x{item['qty']}\n"
    
    if order['tracking_no']:
        res += f"- **物流单号**: {order['tracking_no']}\n"
    
    return res

@mcp.tool()
def logistics_track_17track(tracking_no: str) -> str:
    """
    Query real-time shipping status from 17track.
    Returns the latest status and full trajectory.
    """
    tno = tracking_no.upper()
    steps = MOCK_17TRACK.get(tno)
    if not steps:
        return f"ERROR_404: 17track 未能查询到单号 {tracking_no} 的物流信息。"

    res = f"### 17track 物流追踪 ({tno})\n"
    res += f"**最新状态**: {steps[-1]['status']}\n\n"
    res += "**运输轨迹**:\n"
    for s in reversed(steps):
        res += f"- [{s['time']}] {s['desc']}\n"
    
    return res

@mcp.tool()
def oms_cancel_order(order_id: str) -> str:
    """
    Request to cancel an order. Only allowed for 'pending' orders.
    """
    oid = order_id.upper()
    order = MOCK_CRM.get(oid)
    if not order:
        return f"错误: 订单 {order_id} 不存在。"
    
    if order["status"] == "pending":
        return f"✅ 订单 {oid} 取消申请已提交。系统正在拦截发货，请留意反馈。"
    else:
        return f"❌ 无法取消订单 {oid}。订单状态当前为 '{order['status']}'，请联系人工客服处理。"

@mcp.tool()
def oms_update_address(order_id: str, new_address: str) -> str:
    """
    Update shipping address. Allowed if order is not yet shipped.
    """
    oid = order_id.upper()
    order = MOCK_CRM.get(oid)
    if not order:
        return f"错误: 订单 {order_id} 不存在。"
    
    if order["status"] == "pending":
        return f"✅ 订单 {oid} 的地址已更新为: {new_address}。"
    else:
        return f"❌ 地址修改失败。订单 {oid} 已进入 '{order['status']}' 阶段，无法直接在线修改。"

if __name__ == "__main__":
    mcp.run()
