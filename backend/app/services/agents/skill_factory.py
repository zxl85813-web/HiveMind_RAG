
import os
import json
import re
from typing import Any, Dict, Optional
from loguru import logger
from app.services.llm_gateway import llm_gateway

class SkillFactoryService:
    """
    L5 Strategy: Autonomous Skill Synthesis.
    Converts successful swarm outcomes into reusable AI skills.
    """
    def __init__(self, workspace_root: str = "c:/Users/linkage/Desktop/aiproject"):
        self.workspace_root = workspace_root
        # L5 Hardening: Change to PROPOSALS directory to avoid pollution
        self.skills_base_path = os.path.join(self.workspace_root, "storage", "skill_proposals")

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^a-z0-9\-]', '-', text)
        return re.sub(r'-+', '-', text).strip('-')

    async def synthesize_skill(self, task_name: str, code_content: str, description: str):
        """
        Takes synthesized code and creates a SKILL PROPOSAL for human review.
        """
        skill_slug = self._slugify(task_name)
        skill_path = os.path.join(self.skills_base_path, skill_slug)
        
        logger.info(f"[SkillFactory] Generating SKILL PROPOSAL: {skill_slug}")
        
        if not os.path.exists(skill_path):
            os.makedirs(skill_path, exist_ok=True)
            os.makedirs(os.path.join(skill_path, "scripts"), exist_ok=True)
            os.makedirs(os.path.join(skill_path, "library"), exist_ok=True)

        # 1. Generate SKILL.md with a PROPOSAL header
        prompt = f"""
        You are a Skill Architect. Create a 'SKILL.md' proposal for a new agent skill.
        Skill Name: {task_name}
        Core Implementation:
        ```python
        {code_content}
        ```
        Description: {description}
        
        IMPORTANT: Add a '### 🚦 PROPOSAL STATUS: PENDING REVIEW' header at the top.
        Explain WHY this is worth keeping as a project-specific skill.
        """
        
        logger.debug("[SkillFactory] Generating PROPOSAL documentation...")
        doc_res = await llm_gateway.call_tier(tier=1, prompt=prompt, system_prompt="You are a Technical Architect.")
        
        doc_content = doc_res.content

        # 2. Write assets to proposal dir
        with open(os.path.join(skill_path, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(doc_content)
            
        with open(os.path.join(skill_path, "library", "implementation.py"), "w", encoding="utf-8") as f:
            f.write(code_content)
            
        logger.warning(f"⚠️ [SkillFactory] New Skill Proposal '{skill_slug}' created. Use 'approve_skill.py' to activate.")
        return skill_slug

skill_factory = SkillFactoryService()
