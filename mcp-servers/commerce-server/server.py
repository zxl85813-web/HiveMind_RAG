import os
import re
import asyncio
import httpx
from datetime import datetime
from fastmcp import FastMCP
from msal import PublicClientApplication

# --- Configuration & Auth ---
# Note: Use environment variables for production keys
TRACK17_API_KEY = os.getenv("TRACK17_API_KEY", "YOUR_17TRACK_TOKEN")
D365_BASE_URL = "https://ecoflow-dev.api.crm4.dynamics.com/api/data/v9.2/"
D365_USERNAME = os.getenv("D365_USERNAME", "YOUR_D365_EMAIL")
D365_PASSWORD = os.getenv("D365_PASSWORD", "YOUR_D365_PASSWORD")
# Common Public Client ID for Microsoft Dynamics CRM
D365_CLIENT_ID = "51f81489-12ee-4a9e-aaae-a2591f45987d" 
D365_RESOURCE = "https://ecoflow-dev.crm4.dynamics.com"

mcp = FastMCP("UnifiedCommerceSupport")

# --- Client Classes ---

class Dynamics365Client:
    def __init__(self):
        self.access_token = None
        self.token_expiry = 0
        self.app = PublicClientApplication(D365_CLIENT_ID, authority="https://login.microsoftonline.com/organizations")

    async def get_token(self):
        if self.access_token and self.token_expiry > datetime.now().timestamp():
            return self.access_token
        
        # Resource Owner Password Credentials Flow
        result = self.app.acquire_token_by_username_password(
            D365_USERNAME, 
            D365_PASSWORD, 
            scopes=[D365_RESOURCE + "/.default"]
        )
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            self.token_expiry = datetime.now().timestamp() + result.get("expires_in", 3600) - 60
            return self.access_token
        else:
            raise Exception(f"D365 Auth Failed: {result.get('error_description', 'Unknown error')}")

    async def query_order(self, order_id: str):
        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "Prefer": "odata.include-annotations=\"*\""
        }
        
        # Searching salesorders by name (Order Number)
        # Ref: OData query syntax
        filter_query = f"name eq '{order_id}'"
        url = f"{D365_BASE_URL}salesorders?$filter={filter_query}&$expand=salesorderdetails($select=productdescription,quantity,priceperunit)"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("value"):
                    return data["value"][0]
                return None
            else:
                raise Exception(f"D365 Query Failed: {resp.text}")

class Track17Client:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.17track.net/track/v2.2/gettrackinfo"

    async def track(self, tracking_no: str):
        headers = {
            "17token": self.api_key,
            "Content-Type": "application/json"
        }
        payload = [{"number": tracking_no}]
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"17track Error: {resp.text}"}

d365_client = Dynamics365Client()
track17_client = Track17Client(TRACK17_API_KEY)

# --- MCP Tools ---

@mcp.tool()
async def crm_get_order(order_id: str, is_logged_in: bool = False) -> str:
    """
    Get order details from Dynamics 365.
    If not logged in, returns a login prompt.
    """
    if not is_logged_in:
        return "[UI_ACTION: TRIGGER_LOGIN_POPUP]\n为了您的隐私安全，查看订单详情前请先登录您的官网账户。"

    try:
        order = await d365_client.query_order(order_id)
        if not order:
            return f"未找到单号为 {order_id} 的结算记录，请核对后重试。"

        # Formatting result
        res = f"### 订单详情 ({order_id})\n"
        res += f"- **状态**: {order.get('statuscode@OData.Community.Display.V1.FormattedValue', 'Unknown')}\n"
        res += f"- **总金额**: ￥{order.get('totalamount', 0):.2f}\n"
        res += f"- **下单时间**: {order.get('createdon', 'N/A')}\n"
        
        details = order.get("salesorderdetails", [])
        if details:
            res += "\n**购买明细**:\n"
            for d in details:
                res += f"  - {d.get('productdescription', 'Unknown Product')} | 数量: {int(d.get('quantity', 0))} | 单价: ￥{d.get('priceperunit', 0):.2f}\n"
        
        return res
    except Exception as e:
        return f"查询出错: {str(e)}"

@mcp.tool()
async def logistics_track_17track(tracking_no: str) -> str:
    """
    Query real-time shipping status from 17track API v2.2.
    """
    try:
        result = await track17_client.track(tracking_no)
        if "data" in result and result["data"].get("accepted"):
            track = result["data"]["accepted"][0]["track_info"]
            latest = track.get("latest_status", {})
            
            res = f"### 17track 物流追踪 ({tracking_no})\n"
            res += f"**最新状态**: {latest.get('status', 'Unknown')} ({latest.get('description', '')})\n"
            res += f"**更新时间**: {latest.get('time', 'N/A')}\n\n"
            
            events = track.get("events", [])[:3] # Show last 3 events
            if events:
                res += "**运输轨迹 (最近3条)**:\n"
                for e in events:
                    res += f"- [{e.get('time', 'N/A')}] {e.get('description', '')} ({e.get('address', '')})\n"
            
            return res
        return f"查询失败: {result.get('error', '未找到轨迹信息')}"
    except Exception as e:
        return f"物流接口调用失败: {str(e)}"

# --- ID Validation ---
@mcp.tool()
def validate_support_id(val: str) -> str:
    """Validate if the string matches Official, Amazon, eBay, or Shipment App formats."""
    # Official: EFXX-123456 or #12345
    if re.match(r'^EF[A-Z]{2}-\d{6}$|^#\d{5}$', val, re.I): return "OFFICIAL_ORDER"
    # Amazon: 3-7-7
    if re.match(r'^\d{3}-\d{7}-\d{7}$', val): return "AMAZON_ORDER"
    # eBay: 2-5-5
    if re.match(r'^\d{2}-\d{5}-\d{5}$', val): return "EBAY_ORDER"
    return "UNKNOWN"

# --- Email Reply Tools (Ref: DOCX v1.1) ---

@mcp.tool()
def analyze_incoming_email(content: str) -> dict:
    """
    Formal AI Classifier for incoming emails.
    Categorizes into L1-L5 and identifies specific business intents.
    """
    # In production, this would call an LLM with the following prompt:
    # "Classify this email based on: [L1: Logistics, L2: Lifecycle, L3: Product, L4: Security, L5: Others]"
    
    content_lower = content.lower()
    
    # Advanced logic (Simulation of LLM reasoning)
    intent_map = {
        "logistics_inquiry": (["where", "track", "delivery", "shipping", "receive", "status", "package"], "L1"),
        "order_cancel": (["cancel", "stop", "don't want"], "L2"),
        "address_change": (["address", "location", "ship to"], "L2"),
        "payment_issue": (["pay", "refund", "twice", "money", "cost", "charge"], "L2"),
        "after_sales": (["warranty", "broken", "repair", "replace", "damage"], "L3"),
        "product_usage": (["how to", "river", "delta", "solar", "panel", "connect", "use"], "L3"),
        "membership_inquiry": (["vip", "member", "point", "reward", "rights"], "L3"),
        "chitchat": (["great", "good", "thanks", "love"], "L5"),
    }
    
    best_intent = "general"
    best_level = "L5"
    max_matches = 0
    
    for intent, (keywords, level) in intent_map.items():
        matches = sum(1 for kw in keywords if kw in content_lower)
        if matches > max_matches:
            max_matches = matches
            best_intent = intent
            best_level = level
    
    # Manual overrides for conflicting terms (Simulation of priority-based reasoning)
    if "cancel" in content_lower: best_intent, best_level = "order_cancel", "L2"
    elif "address" in content_lower: best_intent, best_level = "address_change", "L2"
    elif "track" in content_lower or "where" in content_lower: 
        if "broke" in content_lower or "warranty" in content_lower:
            best_intent, best_level = "after_sales", "L3"
        else:
            best_intent, best_level = "logistics_inquiry", "L1"
    elif "delivered" in content_lower and "not" in content_lower:
        best_intent, best_level = "logistics_issue", "L1"
    
    return {
        "scoring_level": best_level,
        "intent": best_intent,
        "confidence": 0.85 + (0.1 if max_matches > 1 else 0),
        "reasoning": f"Detected keywords related to {best_intent}. Priority mapped to {best_level}.",
        "timestamp": datetime.now().isoformat()
    }

@mcp.tool()
def generate_email_draft(email_context: dict) -> str:
    """Generate an AI email draft based on CRM data and intent."""
    intent = email_context.get("intent", "general")
    customer = email_context.get("customer_name", "Valued Customer")
    order_id = email_context.get("order_id", "N/A")
    
    res = f"--- DRAFT EMAIL ({intent.upper()}) ---\n"
    res += f"Subject: Regarding your order {order_id} update\n\n"
    res += f"Dear {customer},\n\nWe are processing your request. "
    res += f"Current Status: {email_context.get('status', 'Checking...')}\n"
    res += "\nBest regards,\nEcoFlow Support Team\n--- END ---"
    return res

if __name__ == "__main__":
    mcp.run()
