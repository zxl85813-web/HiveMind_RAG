
import os
import shutil
import sys
from loguru import logger

def approve_skill(skill_slug: str):
    workspace_root = r"c:\Users\linkage\Desktop\aiproject"
    proposal_path = os.path.join(workspace_root, "storage", "skill_proposals", skill_slug)
    final_path = os.path.join(workspace_root, ".agent", "skills", skill_slug)

    if not os.path.exists(proposal_path):
        logger.error(f"❌ Proposal '{skill_slug}' not found in storage/skill_proposals/")
        return

    logger.info(f"🚀 [Approver] Activating Skill: {skill_slug}")
    
    # Ensure target dir exists
    if os.path.exists(final_path):
        logger.warning(f"Overwriting existing skill at {final_path}")
        shutil.rmtree(final_path)

    # Move logic
    shutil.copytree(proposal_path, final_path)
    
    # 📝 Cleanup: Update SKILL.md to remove PROPOSAL status
    skill_md_path = os.path.join(final_path, "SKILL.md")
    if os.path.exists(skill_md_path):
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove the proposal header
        clean_content = content.replace("### 🚦 PROPOSAL STATUS: PENDING REVIEW", "### ✅ STATUS: ACTIVE (Human Approved)")
        
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(clean_content)

    logger.info(f"✅ [Approver] Skill '{skill_slug}' is now ACTIVE and visible to all agents.")
    
    # Clean up proposal
    # shutil.rmtree(proposal_path) # Keep it or remove it? Let's keep for history.

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python approve_skill.py <skill_slug>")
        sys.exit(1)
    
    approve_skill(sys.argv[1])
