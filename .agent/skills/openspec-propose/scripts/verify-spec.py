import yaml
import os
import sys
from pathlib import Path

def verify_change(name: str):
    change_path = Path("openspec/changes") / name
    print(f"🧐 Auditing OpenSpec Change: {name}")
    
    if not change_path.exists():
        print(f"❌ Error: Change directory '{change_path}' not found.")
        sys.exit(1)
        
    config_file = change_path / ".openspec.yaml"
    if not config_file.exists():
        print(f"❌ Error: .openspec.yaml missing.")
        sys.exit(1)
        
    # Check for mandatory artifacts
    artifacts = ["proposal", "design", "tasks"]
    missing = []
    for art in artifacts:
        art_file = change_path / f"{art}.md"
        if not art_file.exists():
            missing.append(art)
            
    if missing:
        print(f"⚠️ Warning: Missing core artifacts: {', '.join(missing)}")
    else:
        print("✅ Core artifacts present.")
        
    print("🚀 Ready for apply!")
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
         print("Usage: python verify-spec.py <change_name>")
         sys.exit(1)
    verify_change(sys.argv[1])
