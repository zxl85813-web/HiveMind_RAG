
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import async_session_factory
from app.models.agents import ReflectionEntry, ReflectionType, ReflectionSignalType

async def solidify_l4_lessons():
    logger.info("🏛️ [L4-SOLIDIFICATION] Translating Adversarial Lessons into System Directives...")

    directives = [
        "MANDATORY ADVERSARIAL REVIEW: For all security-critical tasks, the plan MUST include a second diverse 'ReviewerAgent' to challenge the 'CodeAgent' findings.",
        "STRICT EVIDENCE CHAINING: Conclusions drawn without retrieved authoritative sources (OWASP/PCI/etc) will be REJECTED by the L4 Gate.",
        "PROCESS-PLAN SYNC: The execution trace MUST match the promised adversarial methodology in the Supervisor Reasoning."
    ]

    async with async_session_factory() as session:
        for d in directives:
            reflection = ReflectionEntry(
                type=ReflectionType.ERROR_CORRECTION,
                signal_type=ReflectionSignalType.INSIGHT,
                agent_name="L4-Auditor-General",
                topic="Security_Governance",
                match_key="security login audit backdoor",
                summary=f"New L4 Governance Rule: {d[:50]}...",
                details={
                    "analysis": {
                        "root_cause": "Process Dishonesty / Missing Friction",
                        "cognitive_directive": d
                    }
                },
                confidence_score=1.0,
                action_taken="DIRECTIVE_ENFORCED"
            )
            session.add(reflection)
        
        await session.commit()
        logger.info(f"✅ Successfully solidified {len(directives)} evolutionary directives.")

if __name__ == "__main__":
    asyncio.run(solidify_l4_lessons())
