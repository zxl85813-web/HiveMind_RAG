import httpx
import asyncio
import time

async def test_conn():
    print("Testing HTTPX direct connection to Moonshot...")
    url = "https://api.moonshot.cn/v1/models"
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            print(f"Status: {resp.status_code} | Duration: {time.time()-start:.2f}s")
            print(f"Body: {resp.text[:200]}...")
    except Exception as e:
        print(f"❌ HTTPX FAILED: {e} | Took {time.time()-start:.2f}s")

if __name__ == "__main__":
    asyncio.run(test_conn())
