import asyncio
import sys
from pathlib import Path

# 🏗️ [Path Fix]: Allow script to run independently
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.services.governance.prompt_service import prompt_service

async def seed_prompts():
    print("🚀 Seeding initial prompts into governance registry...")
    
    # 1. SmartGrep Expansion Prompt
    # Original from smart_grep_service.py
    smart_grep_content = """You are a search keyword expander. Given a technical query, output 8-12 related keywords/synonyms separated by commas. Include the original terms. No other text.
Query: {query}
Output:"""
    
    await prompt_service.register_prompt(
        slug="smart_grep_expansion",
        version="1.0.0",
        content=smart_grep_content,
        is_current=True,
        recommended_model="deepseek-ai/DeepSeek-V3",
        change_log="Migrated from hardcoded string in smart_grep_service.py"
    )

    # 2. Episodic Summary Prompt
    # Original from episodic_service.py:29
    # _EPISODE_SUMMARY_PROMPT = """You are a critical memory summarizer. 
    # Extract the core technical conflict, decision, and outcome from this user session.
    # User Session: {session}
    # Output:"""
    episodic_summary_content = """You are a critical memory summarizer. 
Extract the core technical conflict, decision, and outcome from this user session.
User Session: {session}
Output:"""

    await prompt_service.register_prompt(
        slug="episodic_summary",
        version="1.0.0",
        content=episodic_summary_content,
        is_current=True,
        recommended_model="deepseek-ai/DeepSeek-V3",
        change_log="Migrated from hardcoded string in episodic_service.py"
    )
    
    print("✅ Initial prompts seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_prompts())
