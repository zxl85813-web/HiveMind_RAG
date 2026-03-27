import sqlite3
from pathlib import Path

def drill_scenario_f():
    db_path = Path("test_swarm.db")
    if not db_path.exists():
        print("Database not found.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Find the trace for the JWT retry scenario (Scenario F)
    # Search for the query containing '再次尝试设计 JWT'
    cursor.execute("SELECT id, triage_reasoning, status FROM obs_swarm_traces WHERE query LIKE '%再次尝试设计 JWT%' ORDER BY created_at DESC LIMIT 1")
    trace = cursor.fetchone()
    
    if not trace:
        print("Scenario F trace not found yet. It may still be running.")
        return
        
    tid, reasoning, status = trace
    print(f"🚀 [Scenario F Trace: {tid}] Status: {status}")
    print("\n--- 🧠 预置反思与决策分析 (Cognitive Recall) ---")
    print(reasoning)
    
    # 2. Extract Tasks and Checkpoints
    print("\n--- 🏗️ 生成的任务指令 (Mandated Checkpoints) ---")
    cursor.execute("SELECT agent_name, instruction, status FROM obs_swarm_spans WHERE swarm_trace_id = ? ORDER BY created_at", (tid,))
    spans = cursor.fetchall()
    
    for s in spans:
        print(f"\n[{s[0]}] Status: {s[2]}")
        print(f"Instruction: {s[1]}")
        
    # 3. Memory Verification
    print("\n--- 💾 记忆回溯源 (Memory Context Source) ---")
    # This reasoning should ideally mention the GAP feedback from the previous run
    if "XSS" in reasoning or "correction" in reasoning.lower():
        print("✅ SUCCESS: Supervisor correctly recalled the previous GAP and included it in the plan.")
    else:
        print("⚠️ FEEDBACK: The Supervisor might have generalized the solution instead of explicit recall.")

if __name__ == "__main__":
    drill_scenario_f()
