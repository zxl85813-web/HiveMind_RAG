import asyncio
from app.auth.security import create_access_token, decode_access_token
from app.core.config import settings

def test_token_loop():
    print(f"DEBUG: SECRET_KEY = {settings.SECRET_KEY}")
    payload = {"sub": "admin-user"}
    token = create_access_token(payload)
    print(f"DEBUG: Generated Token = {token}")
    
    try:
        decoded = decode_access_token(token)
        print(f"DEBUG: Decoded Payload = {decoded}")
        if decoded.get("sub") == payload["sub"]:
            print("SUCCESS: Token round-trip works!")
        else:
            print("FAILURE: Payload mismatch!")
    except Exception as e:
        print(f"FAILURE: Token decoding error: {e}")

if __name__ == "__main__":
    test_token_loop()
