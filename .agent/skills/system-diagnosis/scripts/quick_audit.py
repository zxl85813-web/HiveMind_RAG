import json
from pathlib import Path
from datetime import datetime, timedelta

def quick_audit(minutes=10):
    log_dir = Path("backend/logs")
    if not log_dir.exists():
        log_dir = Path("logs") # fallback
        
    cutoff = datetime.now() - timedelta(minutes=minutes)
    
    errors = []
    infos = []
    
    log_files = sorted(list(log_dir.glob("*.log")), reverse=True)
    
    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        record = data.get("record", {})
                        ts_str = record.get("time", {}).get("repr", "")
                        # Simple time check if possible, or just take last files
                        
                        level = record.get("level", {}).get("name", "INFO")
                        msg = record.get("message", "")
                        platform = record.get("extra", {}).get("platform", "BE")
                        module = record.get("extra", {}).get("module", "unknown")
                        
                        entry = f"[{ts_str}] {platform} | {level} | {module} | {msg}"
                        
                        if level == "ERROR":
                            errors.append(entry)
                        else:
                            infos.append(entry)
                    except:
                        continue
        except:
            continue
            
    print(f"\n--- 🕵️ Quick System Audit (Last {minutes}m) ---")
    print(f"Total Errors Found: {len(errors)}")
    if errors:
        print("\n[🚨 Recent Errors]")
        for e in errors[-10:]:
            print(e)
            
    print("\n[ℹ️ Recent Activity]")
    for i in infos[-5:]:
        print(i)
    print("-------------------------------------------\n")

if __name__ == "__main__":
    quick_audit()
