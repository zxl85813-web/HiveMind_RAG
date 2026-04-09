
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger
from sqlmodel import select

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import init_db, async_session_factory
from app.models.observability import SwarmTrace, SwarmSpan, TraceStatus
from app.services.llm_gateway import llm_gateway

class L4ProcessIntegrityGate:
    """
    L4 Process Integrity Gate.
    'Outcome is binary, Process is structural.'
    This gate audits the reasoning chain of a Swarm for structural integrity.
    """

    async def audit_latest_trace(self):
        logger.info("🛡️ [L4-GATE] Starting Process Integrity Audit...")
        
        async with async_session_factory() as session:
            # 1. Get the latest successful trace
            statement = select(SwarmTrace).order_by(SwarmTrace.created_at.desc()).limit(1)
            result = await session.exec(statement)
            trace = result.first()

            if not trace:
                logger.warning("No traces found for audit.")
                return

            # 2. Get all spans (steps) for this trace
            span_statement = select(SwarmSpan).where(SwarmSpan.swarm_trace_id == trace.id).order_by(SwarmSpan.created_at)
            span_result = await session.exec(span_statement)
            spans = span_result.all()

            logger.info(f"Auditing Trace: {trace.id} | Query: {trace.query} | Steps: {len(spans)}")

            # 3. Construct the 'Process View' for the Judge
            process_log = []
            process_log.append(f"Global Plan Reasoning: {trace.triage_reasoning}")
            
            # Extract historical directives from the prompt context if possible, 
            # or we can pull them again from the same logic used in MemoryBridge
            process_log.append("--- [AUDIT TARGET: SYSTEM DIRECTIVES] ---")
            # For simplicity in the script, we assume the judge can see them in the spans or reasoning.
            # But let's be explicit:
            process_log.append(f"Trace Status: {trace.status}")

            for i, span in enumerate(spans):
                process_log.append(
                    f"Step {i+1} [{span.agent_name}]:\n"
                    f"Instruction: {span.instruction}\n"
                    f"Output: {span.output[:1000]}..." # Limit for probe
                )

            full_process = "\n\n".join(process_log)

            # 4. Call L4 Semantic Judge
            judge_prompt = f"""
            ### PROCESS INTEGRITY AUDIT (L4 GOVERNANCE)
            Original Query: {trace.query}
            
            FULL REASONING CHAIN:
            {full_process}
            
            Evaluate this reasoning chain against the 'HiveMind Process Excellence' criteria:
            1. EVIDENCE LINEAGE: Did conclusions derive directly from previous steps or retrieved context? (Reject 'Magic Conclusions')
            2. CRITICAL FRICTION: Did Reviewer Agents find gaps, or did they just 'Rubber Stamp'? (Reject lack of friction)
            3. TRUTHFULNESS: Are there any logical contradictions between steps?
            4. COMPLIANCE CHECK: Did the Supervisor explicitly follow the '!!! [SYSTEM DIRECTIVE]' found in the context?
            
            VULNERABILITY DETECTION:
            - DANGEROUS_LUCK: Correct result but wrong/lazy process.
            - PROCESS_POLLUTION: Substantial irrelevant info introduced.
            - COGNITIVE_DISHONESTY: Supervisor claimed to follow a directive but violated it in the task instructions.
            
            FINAL VERDICT JSON:
            {{
              "verdict": "INTEGRITY_PASS" | "INTEGRITY_FAIL" | "DANGEROUS_LUCK",
              "reasoning_integrity_score": 0.0-1.0,
              "findings": ["finding 1", "finding 2"],
              "improvement_plan": "Specific action for L4 evolution"
            }}
            """

            response = await llm_gateway.call_tier(
                tier=3, # Use Tier-3 for auditing
                prompt=judge_prompt,
                system_prompt="You are the Chief Evolution Auditor. You value the 'How' more than the 'What'.",
                response_format={"type": "json_object"}
            )

            audit_res = json.loads(response.content)
            
            # 5. Update Trace Status if integrity fails
            if audit_res.get("verdict") in ["INTEGRITY_FAIL", "DANGEROUS_LUCK"]:
                logger.warning(f"🚨 Process integrity compromised: {audit_res.get('verdict')}")
                trace.status = TraceStatus.REJECTED if audit_res.get("verdict") == "INTEGRITY_FAIL" else trace.status
                # We could add an 'integrity_comment' field to SwarmTrace in a future migration
            else:
                 logger.success("✅ Process integrity verified.")

            # Record final report
            report_path = Path(r"c:\Users\linkage\Desktop\aiproject\docs\evaluation\L4_INTEGRITY_REPORT.md")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            md_report = f"""# 🛡️ L4 过程完整性审计报告 (L4 Process Integrity Report)

> **审计时间**: {datetime.now().isoformat()}
> **关联 Trace**: `{trace.id}`
> **初始查询**: {trace.query}

## ⚖️ 审计结论 (Verdict)
### **状态**: {audit_res.get('verdict')}
### **完整性得分**: {audit_res.get('reasoning_integrity_score')}

## 🔍 主要发现 (Findings)
{chr(10).join([f'- {f}' for f in audit_res.get('findings', [])])}

## 🧠 L4 进化路线 (Evolution Plan)
{audit_res.get('improvement_plan')}

---
### 🛠️ 过程回放 (Process Trace Breakdown)
{full_process[:2000]}... (truncated for report)
"""
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(md_report)

            logger.info(f"Audit report generated at: {report_path}")

async def main():
    gate = L4ProcessIntegrityGate()
    await gate.audit_latest_trace()

if __name__ == "__main__":
    asyncio.run(main())
