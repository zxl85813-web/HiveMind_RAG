import os
import time
import json
import requests
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

# --- 1. Environment and Configuration ---
BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")
load_dotenv(BASE_DIR / "backend" / ".env")

# API Config
API_URL = "http://127.0.0.1:8000/api/v1/chat/completions"
# Mock payload for benchmarking
PAYLOAD = {
    "message": "Explain the HiveMind Intelligence Swarm architecture and its 4-realm ontology.",
    "stream": True,
    "conversation_id": None
}

# Neo4j Config
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://121.37.20.14:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DRIVER = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def run_benchmark():
    print(f"🚀 Starting HMER Benchmark at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    ttft = None
    total_latency = None
    token_count = 0
    full_response = ""

    try:
        # Use a real request to the backend
        print(f"📡 Requesting: {API_URL}")
        response = requests.post(API_URL, json=PAYLOAD, stream=True, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return None

        # Process stream
        for line in response.iter_lines():
            if line:
                if ttft is None:
                    ttft = (time.time() - start_time) * 1000  # Convert to ms
                    print(f"⏱️  Time to First Token (TTFT): {ttft:.2f}ms")
                
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        # Extract content using HiveMind native format
                        if data.get("type") == "content":
                            content = data.get("delta", "")
                            if content:
                                full_response += content
                                token_count += 1 
                        elif data.get("type") == "session_created":
                            print(f"🆔 Session Created: {data.get('id')}")
                    except Exception:
                        pass
        
        total_latency = (time.time() - start_time) * 1000 # ms
        print(f"⌛ Total Latency: {total_latency:.2f}ms")
        print(f"🔢 Estimated Tokens: {token_count}")

        metric_data = {
            "timestamp": int(time.time()),
            "ttft": ttft,
            "latency": total_latency,
            "tokens": token_count,
            "throughput": (token_count / (total_latency / 1000)) if total_latency > 0 else 0,
            "status": "SUCCESS"
        }
        return metric_data

    except Exception as e:
        print(f"❌ Benchmark execution failed: {e}")
        return {
            "timestamp": int(time.time()),
            "status": "FAILED",
            "error": str(e)
        }

def inject_to_neo4j(metrics):
    if not metrics:
        return

    print(f"🧪 Injecting MetricNode to Neo4j...")
    with DRIVER.session() as session:
        # Create MetricNode and Link to Architecture/GOV-001
        session.run("""
            MERGE (m:MetricNode {scope: 'HMER-Architecture-Checkup', timestamp: $ts})
            SET m.ttft = $ttft,
                m.latency = $latency,
                m.tokens = $tokens,
                m.throughput = $throughput,
                m.status = $status,
                m.type = 'Performance'
            
            WITH m
            MATCH (g:CognitiveAsset {id: 'GOV-001-DEVELOPMENT_GOVERNANCE'})
            MERGE (g)-[:AUDITED_BY]->(m)
            
            WITH m
            MATCH (d:CognitiveAsset {id: 'DES-003-BACKEND_ARCHITECTURE'})
            MERGE (d)-[:HAS_PERFORMANCE_METRIC]->(m)
        """, ts=metrics['timestamp'], 
             ttft=metrics.get('ttft'), 
             latency=metrics.get('latency'), 
             tokens=metrics.get('tokens'),
             throughput=metrics.get('throughput'),
             status=metrics['status'])
    
    print("✅ Neo4j Metric Injection Complete.")

if __name__ == "__main__":
    # Ensure backend is up for a few seconds before running if we had just started it
    # But user said it's on.
    results = run_benchmark()
    if results:
        inject_to_neo4j(results)
    DRIVER.close()
