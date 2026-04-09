
import sys
import json
from pathlib import Path
from loguru import logger

# Configuration
L3_BOARD_PATH = Path(r"docs/evaluation/L3_QUALITY_BOARD.md")
MIN_REQUIRED_SCORE = 0.60

def gate_l3_intelligence():
    logger.info("🛡️ [L3-GATE] Verifying Agentic Intelligence Quality Gate...")
    
    # 1. Resolve path relative to backend or root
    target_path = L3_BOARD_PATH
    if not target_path.exists():
        # Try relative to parent if run from backend
        target_path = Path("..") / L3_BOARD_PATH
        if not target_path.exists():
            logger.error(f"❌ L3 Quality Board not found at {L3_BOARD_PATH}. Run scripts/l3_dashboard_sync.py first.")
            sys.exit(1)

    # 2. Parse Markdown to find the score
    # Look for: | **平均智能分 (Avg Score)** | **0.85** |
    content = target_path.read_text(encoding="utf-8")
    import re
    match = re.search(r"\|\s*\*\*平均智能分 \(Avg Score\)\*\*\s*\|\s*\*\*([\d\.]+)\*\*\s*\|", content)
    
    if not match:
        logger.error("❌ Could not parse Average Score from Dashboard.")
        sys.exit(1)
        
    avg_score = float(match.group(1))
    logger.info(f"📊 Current Avg Intelligence Score: {avg_score}")
    
    if avg_score < MIN_REQUIRED_SCORE:
        logger.critical(f"🛑 [GATE-FAIL] Intelligence score {avg_score} is below threshold {MIN_REQUIRED_SCORE}!")
        logger.error("Check docs/evaluation/L3_QUALITY_BOARD.md for failure details.")
        sys.exit(1)
        
    logger.success(f"✅ [GATE-PASS] L3 Intelligence validation successful ({avg_score} >= {MIN_REQUIRED_SCORE}).")
    sys.exit(0)

if __name__ == "__main__":
    gate_l3_intelligence()
