import requests
import json
import os
import sys
from pathlib import Path

# Paths
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

from app.core.config import settings

def test_ark_raw():
    print("🚀 Testing RAW Ark API with current .env settings...")
    api_key = settings.ARK_API_KEY or settings.LLM_API_KEY
    base_url = settings.ARK_BASE_URL or settings.LLM_BASE_URL
    model = settings.ARK_MODEL
    
    url = f"{base_url}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model, 
        "messages": [{"role": "user", "content": "hello"}]
    }
    
    print(f"URL: {url}")
    print(f"Model: {model}")
    print(f"Key Prefix: {api_key[:10]}...")
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"❌ RAW REQUEST FAILED: {e}")

if __name__ == "__main__":
    test_ark_raw()
