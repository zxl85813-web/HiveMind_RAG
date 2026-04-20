import random
import re
from datetime import datetime, timedelta
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("UnifiedCommerceSupport")

# --- Regex for ID validation (Ref: PDF Page 8, 9) ---
RE_OFFICIAL_ORDER = re.compile(r'^EF[A-Z]{2}-\d{6}$|^#\d{5}$', re.IGNORECASE)
RE_AMAZON_ORDER = re.compile(r'^\d{3}-\d{7}-\d{7}$', re.IGNORECASE)
RE_EBAY_ORDER = re.compile(r'^\d{2}-\d{5}-\d{5}$', re.IGNORECASE)
RE_SHIPMENT_APP = re.compile(r'^NA\d{11}$|^CRM-RE\d{10}-\d$', re.IGNORECASE)

# --- SKU to Model Mapping ---
SKU_MAPPING = {
    "P001": "EcoFlow DELTA 2 (Model: EF-DELTA2-1024)",
    "P002": "Portable Solar Panel (Model: EF-PV-160W)",
    "P003": "River 2 Pro (Model: EF-RIVER2PRO-768)"
}

# --- Email Templates (Ref: DOCX 3.5) ---
EMAIL_TEMPLATES = {
    "logistics_inquiry": {
        "subject": "Regarding your order {order_id} shipping status",
        "body": "Dear {customer},\n\nThank you for reaching out. We've checked the status of your order {order_id}. Your package is currently {status}.\nLatest update: {track_desc}\n\nBest regards,\nCustomer Support Team"
    },
    "order_cancel_confirm": {
        "subject": "Order Cancellation Request: {order_id}",
        "body": "Dear {customer},\n\nWe have received your request to cancel order {order_id}. Our team is now processing the interception. You will receive a confirmation once it is completed.\n\nBest regards,\nCustomer Support Team"
    }
}

# --- Mock Databases ---
MOCK_CRM = {
    "EFUS-121453": {
        "status": "shipped",
        "items": [{"sku": "P001", "qty": 1, "shipped_qty": 1, "tax_amount": 599.00}],
        "amount": 5999.00,
        "customer": "Cherry Zhang",
        "address": "深圳市南山区科技园",
        "tracking_no": "SF178822930",
        "requires_login": True,
        "equipment_rights": {"warranty": "2028-04-18", "support_tier": "VIP"}
    }
}

MOCK_17TRACK = {
    "SF178822930": [
        {"time": "2026-04-19 08:30", "status": "Delivering", "desc": "Out for delivery by Courier Wang"}
    ]
}

# --- Skills Tools (Commerce) ---

@mcp.tool()
def crm_get_order(order_id: str, is_logged_in: bool = False) -> str:
    """Get order details and equipment rights from CRM/OMS."""
    oid = order_id.upper()
    order = MOCK_CRM.get(oid)
    if not order: return f"ERROR_001: Order {order_id} not found."
    if order["requires_login"] and not is_logged_in:
        return "[UI_ACTION: TRIGGER_LOGIN_POPUP]\nLogin required for sensitive information."
    
    res = f"### Order Details ({oid})\n- Customer: {order['customer']}\n- Status: {order['status']}\n- Items:\n"
    for item in order['items']:
        model = SKU_MAPPING.get(item['sku'], "Unknown")
        res += f"  - {model} (SKU: {item['sku']}) x{item['qty']}\n"
    return res

@mcp.tool()
def logistics_track_17track(tracking_no: str) -> str:
    """Query shipping status from 17track."""
    steps = MOCK_17TRACK.get(tracking_no.upper())
    if not steps: return "ERROR: No tracking info found."
    return f"Latest: {steps[-1]['status']} - {steps[-1]['desc']}"

# --- Email Reply Tools (Ref: DOCX 3.2, 3.4) ---

@mcp.tool()
def analyze_incoming_email(content: str) -> dict:
    """
    Analyze incoming email content for L1-L5 Grading and Intent detection.
    (Ref: DOCX 3.2.1)
    """
    content_lower = content.lower()
    
    # Simple Mock Scoring Logic
    score = "L3" # Default
    intent = "general"
    confidence = 0.85
    
    if "where is my" in content_lower or "tracking" in content_lower:
        score = "L1" # Simple logistics inquiry
        intent = "logistics_inquiry"
    elif "cancel" in content_lower:
        score = "L2" # Requires decision context
        intent = "order_cancel"
    
    return {
        "scoring_level": score,
        "intent": intent,
        "confidence": confidence,
        "summary": "AI detected a potential " + intent + " request."
    }

@mcp.tool()
def generate_email_draft(email_context: dict) -> str:
    """
    Generate an AI email draft based on CRM data and intent.
    (Ref: DOCX 3.4)
    """
    intent = email_context.get("intent")
    customer = email_context.get("customer_name", "Valued Customer")
    order_id = email_context.get("order_id", "N/A")
    
    template = EMAIL_TEMPLATES.get(intent)
    if not template:
        return "I'm sorry, I couldn't find a suitable template for this request. Drafting manual reply..."
    
    # Fill template
    subject = template["subject"].format(order_id=order_id)
    body = template["body"].format(
        customer=customer, 
        order_id=order_id, 
        status=email_context.get("order_status", "processing"),
        track_desc=email_context.get("latest_track", "to be updated")
    )
    
    return f"--- DRAFT EMAIL ---\nSubject: {subject}\n\n{body}\n--- END OF DRAFT ---"

if __name__ == "__main__":
    mcp.run()
