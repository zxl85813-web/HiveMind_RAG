
import asyncio
import sys
import os
from pathlib import Path
from loguru import logger

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.agents.skill_factory import skill_factory

async def run_l5_skill_factory_demo():
    logger.info("[L5-FACTORY] Starting L5 Proposal-Based Skill Synthesis...")

    task_name = "Flask JWT Redis Governance"
    code_content = "class TokenBlacklist: pass"
    description = "Advanced JWT revocation management using Redis."

    logger.info(f"Step 1: Commencing proposal for '{task_name}'...")
    skill_slug = await skill_factory.synthesize_skill(
        task_name=task_name,
        code_content=code_content,
        description=description
    )

    # 1. Check in Proposals
    proposal_path = os.path.join(r"c:\Users\linkage\Desktop\aiproject\storage\skill_proposals", skill_slug)
    final_path = os.path.join(r"c:\Users\linkage\Desktop\aiproject\.agent\skills", skill_slug)

    print("\n" + "="*60)
    print("DEMO STAGE 1: PROPOSAL VERIFICATION")
    print("="*60)
    if os.path.exists(proposal_path):
        print(f"PASS: Proposal created at {proposal_path}")
    else:
        print(f"FAIL: Proposal missing at {proposal_path}")

    if not os.path.exists(final_path):
        print("PASS: Skill NOT yet active in workspace (Governance Intact).")
    else:
        print("FAIL: Skill exists in workspace prematurely!")

    # 2. Approve
    print("\n" + "="*60)
    print("DEMO STAGE 2: HUMAN APPROVAL")
    print("="*60)
    
    # Simulate running the approve script
    import subprocess
    cmd = [sys.executable, str(backend_dir / "scripts" / "approve_skill.py"), skill_slug]
    subprocess.run(cmd, check=True)

    if os.path.exists(os.path.join(final_path, "SKILL.md")):
        print("PASS: Skill is now ACTIVE in .agent/skills/")
        with open(os.path.join(final_path, "SKILL.md"), "r", encoding="utf-8") as f:
            content = f.read()
            if "STATUS: ACTIVE (Human Approved)" in content:
                print("PASS: SKILL.md metadata updated to ACTIVE.")
    else:
        print("FAIL: Skill activation failed.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_l5_skill_factory_demo())
