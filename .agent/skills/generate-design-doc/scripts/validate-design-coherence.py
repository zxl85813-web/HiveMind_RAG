import re
import sys
from pathlib import Path

def validate_design(file_path: str):
    print(f"🔍 Checking design document: {file_path}")
    content = Path(file_path).read_text(encoding='utf-8')
    errors = []

    # 1. Check for 4-Tier Sections
    sections = [
        "Architecture Overview",
        "Data Persistence",
        "Backend Services",
        "API Endpoints",
        "Frontend Components"
    ]
    for section in sections:
        if section not in content:
            errors.append(f"Missing mandatory section: {section}")

    # 2. Check for Mermaid Diagrams
    mermaid_blocks = len(re.findall(r'```mermaid', content))
    if mermaid_blocks < 2:
        errors.append(f"Insufficient Mermaid diagrams (found {mermaid_blocks}, need at least 2: Flow and ER)")

    # 3. Check for specific markers
    if "DES-" not in content:
        errors.append("Document lacks a proper DES-NNN identifier.")

    if "[ACTION:" in content:
        # Check if action format is valid if any
        pass

    if errors:
        print("❌ Validation failed:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("✅ Design document looks solid and compliant with Phase 2 standards.")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate-design-coherence.py <path_to_des_md>")
        sys.exit(1)
    validate_design(sys.argv[1])
