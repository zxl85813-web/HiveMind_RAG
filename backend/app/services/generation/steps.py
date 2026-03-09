# ruff: noqa: W293

import abc
import csv
import os
import time

from app.services.retrieval import get_retrieval_service

from .protocol import DesignResult, GenerationContext


class BaseGenerationStep(abc.ABC):
    @abc.abstractmethod
    async def execute(self, ctx: GenerationContext):
        pass


class ContextRetrievalStep(BaseGenerationStep):
    """
    Step 1: Get Context from RetrievalService.
    """

    async def execute(self, ctx: GenerationContext):
        service = get_retrieval_service()
        try:
            # Assume RetrievalService.run exists (from my earlier impl)
            # Or retrieve(query, kb_ids, ...)
            # Let's check retrieval/pipeline.py signature: run(query, collection_names, ...)
            docs = await service.run(query=ctx.task_description, collection_names=ctx.kb_ids, top_k=5, top_n=3)
            ctx.retrieved_content = [d.page_content for d in docs]
            ctx.log("Retrieval", f"Found {len(docs)} relevant docs.")
        except Exception as e:
            ctx.log("Retrieval", f"Error: {e}")


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
            ctx.log("Drafting", f"LLM Failed: {e}. Using fallback.")
            # Fallback Mock
            ctx.draft_content = DesignResult(
                headers=["ID", "Error", "Details"],
                rows=[{"ID": "ERR-01", "Error": "Generation Failed", "Details": str(e)}],
            )


class SelfCorrectionStep(BaseGenerationStep):
    """
    Step 3: Self-Correction.
    Review the draft against constraints or logical consistency.
    """

    async def execute(self, ctx: GenerationContext):
        if not ctx.draft_content:
            return

        from app.core.llm import get_llm_service

        llm = get_llm_service()

        ctx.log("Correction", "Reviewing draft for safety and constraints...")

        draft_json = ctx.draft_content.model_dump_json()

        prompt = f"""
        You are a QA Critic Agent.
        
        # Task
        {ctx.task_description}
        
        # Current Draft
        {draft_json}
        
        # Instruction
        Review the draft for logic gaps, safety issues, or missing requirements.
        - If the draft is good, return the SAME JSON.
        - If issues exist, correct the rows or add missing ones.
        - Return ONLY valid JSON with 'headers' and 'rows'.
        """

        try:
            import json

            response = await llm.chat_complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temp for critic
                json_mode=True,
            )
            data = json.loads(response)

            if "headers" in data and "rows" in data:
                ctx.draft_content = DesignResult(headers=data["headers"], rows=data["rows"])
                ctx.log("Correction", "Draft refined by Critic Agent.")

        except Exception as e:
            ctx.log("Correction", f"Critic failed: {e}. Keeping original draft.")


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
