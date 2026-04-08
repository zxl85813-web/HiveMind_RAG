# ruff: noqa: W293

import abc
import csv
import json
import os
import time
from typing import Any

from pydantic import BaseModel, Field

from app.services.retrieval import get_retrieval_service

from .protocol import DesignResult, GenerationContext


class CritiqueReport(BaseModel):
    """Structured output from the Critic Agent per iteration."""
    score: int = Field(description="Quality score from 1 to 10. 10 = perfect.")
    issues: list[str] = Field(default_factory=list, description="Specific issues found. Empty if none.")
    corrected_draft: dict[str, Any] = Field(description="The corrected JSON with 'headers' and 'rows'.")


class BaseGenerationStep(abc.ABC):
    @abc.abstractmethod
    async def execute(self, ctx: GenerationContext):
        pass


class ContextRetrievalStep(BaseGenerationStep):
    """
    Step 1: Get Context from MemoryService (Multi-Tier).
    """

    async def execute(self, ctx: GenerationContext):
        from app.services.memory.memory_service import MemoryService
        
        user_id = getattr(ctx, "user_id", "default_user")
        memory_svc = MemoryService(user_id=user_id)
        
        try:
            # Multi-Tier Context Retrieval (Radar + Graph + Vector + SmartGrep)
            ctx.log("Retrieval", f"Recalling context for user: {user_id}")
            rich_context = await memory_svc.get_context(query=ctx.task_description)
            
            # Store as a list to match the expectation of subsequent steps
            ctx.retrieved_content = [rich_context] if rich_context.strip() else []
            ctx.log("Retrieval", f"Recalled rich context ({len(rich_context)} chars).")
            
        except Exception as e:
            ctx.log("Retrieval", f"Error during memory-augmented retrieval: {e}")
            ctx.retrieved_content = []


class DraftingStep(BaseGenerationStep):
    """
    Step 2: Active Creating.
    Uses LLM to generate structured content (Design Table).
    """

    async def execute(self, ctx: GenerationContext):
        from app.core.llm import get_llm_service

        llm = get_llm_service()

        ctx.log("Drafting", "Generating initial design table...")

        context_str = "\n\n".join(ctx.retrieved_content[:5])  # Limit context
        prompt = f"""
        You are an Expert Architect Agent.
        
        # Task
        {ctx.task_description}
        
        # Valid Knowledge Context
        {context_str}
        
        # Instruction
        Based on the Context and Task, generate a structured design table.
        Return ONLY valid JSON with two keys: "headers" (list of column names) and "rows" (list of objects).
        Ensure the keys in "rows" match "headers".
        
        # MANDATORY CITATION POLICY (CRITICAL)
        1. Every single row in the "rows" list MUST be grounded in the # Valid Knowledge Context.
        2. You MUST append at least one citation marker [N] (e.g., [1], [2]) at the end of the most descriptive text field for EVERY row.
        3. Even if the information seems obvious, if it can be found in the context, tag it.
        
        # EXAMPLE
        If context [1] mentions "SQLite 3.35+ supports DROP COLUMN", the row should be:
        {{"ID": "SQL-01", "Constraint": "DROP COLUMN", "Details": "Supported in 3.35+ [1]"}}
        
        # PENALTY
        Failure to provide [N] citations for EACH row will result in a hard failure (Score 0) from the automated Quality Grader.
        """

        try:
            import json

            response = await llm.chat_complete(
                messages=[{"role": "user", "content": prompt}], temperature=0.7, json_mode=True
            )
            data = json.loads(response)

            if "headers" in data and "rows" in data:
                # Basic validation
                ctx.draft_content = DesignResult(headers=data["headers"], rows=data["rows"])
                ctx.log("Drafting", f"LLM generated {len(data['rows'])} rows.")
            else:
                raise ValueError("Missing headers or rows in JSON")

        except Exception as e:
            ctx.log("Drafting", f"LLM Failed: {e}. Using descriptive fallback.")
            # Standardised No-Found Fallback (Prevents pipeline from returning None)
            ctx.draft_content = DesignResult(
                headers=["Status", "Details", "Recommendation"],
                rows=[{
                    "Status": "Information Not Found", 
                    "Details": f"System could not generate a design table from current context. (Error: {str(e)[:100]})",
                    "Recommendation": "Try refining the search query or verifying the knowledge base contents."
                }],
            )


class SelfCorrectionStep(BaseGenerationStep):
    """
    Step 3: Iterative Self-Correction (upgraded).

    Runs a Critic Agent loop (max MAX_ITERATIONS rounds):
    - Each round the Critic returns a structured CritiqueReport with a 1-10 score.
    - Loop exits early when score >= PASS_THRESHOLD or no issues remain.
    - Guards against self-confirmation bias with an explicit scoring rubric.
    """

    MAX_ITERATIONS: int = 3
    PASS_THRESHOLD: int = 8  # Score out of 10

    async def execute(self, ctx: GenerationContext):
        if not ctx.draft_content:
            return

        from app.core.llm import get_llm_service
        from app.core.logging import get_trace_logger

        llm = get_llm_service()
        logger = get_trace_logger(__name__)

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            draft_json = ctx.draft_content.model_dump_json(indent=2)
            context_str = "\n\n".join(ctx.retrieved_content[:5])

            prompt = f"""
            You are a QA Critic Agent performing **Iteration {iteration}/{self.MAX_ITERATIONS}**.

            # Original Task
            {ctx.task_description}

        # Valid Knowledge Context (Source of Truth)
        {context_str}

        # Current Draft (to be evaluated)
        {draft_json}

        # Scoring Rubric (1-10)
        - 9-10: Fully complete, factually aligned with Context, correct citations [N] for every row.
        - 7-8:  Minor improvements possible, MOST rows have citations and align with Context.
        - 5-6:  Significant logic gaps OR missing citations OR factual deviations from Context.
        - 1-4:  No citations, or hallucinated facts not present in Context.

        # Instruction
        1. Compare the Draft against the Valid Knowledge Context. 
        2. Score the draft strictly against the rubric above (emphasize factual alignment).
        3. List ALL specific issues found (especially missing facts or hallucinations).
        4. In 'corrected_draft', return the FIXED JSON that incorporates missing data from Context.
           Ensure 'headers' and 'rows' are maintained.

        Return ONLY valid JSON matching this schema:
        {{
          "score": <int 1-10>,
          "issues": ["<issue 1>", "<issue 2>"],
          "corrected_draft": {{ "headers": [...], "rows": [...] }}
        }}
        """

            try:
                response = await llm.chat_complete(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,  # Very low: critic must be conservative
                    json_mode=True,
                )
                data = json.loads(response)
                report = CritiqueReport(**data)

                # Apply the corrected draft
                corrected = report.corrected_draft
                if "headers" in corrected and "rows" in corrected:
                    ctx.draft_content = DesignResult(
                        headers=corrected["headers"],
                        rows=corrected["rows"],
                    )

                ctx.log(
                    "Correction",
                    f"[Iter {iteration}] Score={report.score}/10 | Issues={report.issues}",
                )
                logger.info(
                    f"🔍 Critic Iter {iteration}: score={report.score}, issues={len(report.issues)}"
                )

                # ✅ Early exit: quality is sufficient
                if report.score >= self.PASS_THRESHOLD or not report.issues:
                    ctx.log(
                        "Correction",
                        f"✅ Critic passed at iteration {iteration} (score={report.score}).",
                    )
                    break

            except Exception as e:
                ctx.log("Correction", f"Critic iter {iteration} failed: {e}. Keeping draft.")
                logger.warning(f"⚠️ Critic iteration {iteration} error: {e}")
                break  # Do not retry on parse failure

        else:
            ctx.log("Correction", f"⚠️ Critic hit max iterations ({self.MAX_ITERATIONS}). Using best draft.")


class ExcelExportStep(BaseGenerationStep):
    """
    Step 4: Output Formatting.
    Export to CSV (Excel compatible).
    """

    async def execute(self, ctx: GenerationContext):
        if not ctx.draft_content:
            return

        # Use a temp directory or project root?
        # User asked for Excel output. I'll save to 'exports' dir in backend.
        export_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(export_dir, exist_ok=True)

        filename = f"design_{int(time.time())}.csv"
        filepath = os.path.join(export_dir, filename)

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=ctx.draft_content.headers)
                writer.writeheader()
                writer.writerows(ctx.draft_content.rows)

            ctx.final_artifact_path = filepath
            ctx.log("Export", f"Generated artifact: {filepath}")
        except Exception as e:
            ctx.log("Export", f"Failed to save CSV: {e}")
