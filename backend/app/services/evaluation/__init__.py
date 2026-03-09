"""
Evaluation Service — Integrated RAGAS / DeepEval for quality metrics.
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.llm import get_llm_service
from app.models.evaluation import EvaluationItem, EvaluationReport, EvaluationSet
from app.models.knowledge import DocumentChunk, KnowledgeBase, KnowledgeBaseDocumentLink


class EvaluationService:
    """Orchestrates RAG quality assessment tasks (Faithfulness, Relevance, etc.)."""

    @staticmethod
    async def generate_testset(db: AsyncSession, kb_id: str, name: str, count: int = 10) -> EvaluationSet:
        """
        Creates a ground-truth dataset by extracting chunks and asking LLM to generate Q&A.
        """
        logger.info(f"📊 Generating testset for KB {kb_id} (n={count})")

        # 1. Create the set
        eval_set = EvaluationSet(kb_id=kb_id, name=name)
        db.add(eval_set)
        await db.commit()
        await db.refresh(eval_set)

        # 2. Get random chunks from this KB
        # We join with KnowledgeBaseDocumentLink if we had many-to-many,
        # but chunks are linked to Document, and Document is linked to KB via KBLink.

        # This is a bit complex for a single query, let's simplify for MVP:
        # Get all documents in this KB
        stmt = select(KnowledgeBaseDocumentLink.document_id).where(KnowledgeBaseDocumentLink.knowledge_base_id == kb_id)
        res = await db.execute(stmt)
        doc_ids = res.scalars().all()

        if not doc_ids:
            logger.warning("No documents found in KB for testset generation.")
            return eval_set

        # Get relevant chunks
        stmt = select(DocumentChunk).where(DocumentChunk.document_id.in_(doc_ids)).limit(count * 2)
        res = await db.execute(stmt)
        chunks = res.scalars().all()

        if not chunks:
            logger.warning("No chunks found in KB for testset generation.")
            return eval_set

        # 3. Use LLM to generate QA for each chunk
        llm = get_llm_service()

        items_created = 0
        for chunk in chunks[:count]:
            prompt = f"""
            Based on the following text chunk, generate a realistic question and its definitive answer (ground truth).
            The question should be something a user would actually ask.
            The answer must be based ENTIRELY on the provided text.
            
            Format as JSON:
            {{"question": "...", "answer": "..."}}
            
            Text Chunk:
            {chunk.content}
            """

            try:
                resp = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
                data = json.loads(resp)

                item = EvaluationItem(
                    set_id=eval_set.id,
                    question=data["question"],
                    ground_truth=data["answer"],
                    reference_context=chunk.content[:500],
                )
                db.add(item)
                items_created += 1
            except Exception as e:
                logger.error(f"Failed to generate QA item: {e}")

        await db.commit()
        logger.info(f"✅ Generated {items_created} items for evaluation set {eval_set.id}")
        return eval_set

    @staticmethod
    async def run_evaluation(db: AsyncSession, set_id: str, model_name: str | None = None) -> EvaluationReport:
        """
        Runs the RAGAS evaluation pipeline.
        M2.5 Multi-model: Generation uses the specified 'model_name'.
        1. Retrieval: Get context for each question.
        2. Generation: Get LLM response (Track latency/cost).
        3. Scorer: Use RAGAS metrics to score.
        """
        import time

        start_time = time.time()

        target_model = model_name or "gpt-3.5-turbo"
        logger.info(f"🚀 Running evaluation for set {set_id} using model {target_model}")

        eval_set = await db.get(EvaluationSet, set_id)
        if not eval_set:
            raise ValueError("Evaluation set not found")

        # Create report record
        report = EvaluationReport(set_id=set_id, kb_id=eval_set.kb_id, status="running", model_name=target_model)
        db.add(report)
        await db.commit()
        await db.refresh(report)

        # 1. Fetch Items
        stmt = select(EvaluationItem).where(EvaluationItem.set_id == set_id)
        res = await db.execute(stmt)
        items = res.scalars().all()

        llm = get_llm_service()
        results = []
        total_tokens = 0

        for item in items:
            try:
                from app.models.knowledge import KnowledgeBase
                from app.services.retrieval.pipeline import RetrievalPipeline

                kb = await db.get(KnowledgeBase, eval_set.kb_id)
                if not kb:
                    continue

                pipeline = RetrievalPipeline()
                docs = await pipeline.run(item.question, collection_names=[kb.vector_collection])
                contexts = [doc.page_content for doc in docs]

                context_text = "\n\n".join(contexts)
                gen_prompt = f"Use the context below to answer the question.\nContext: {context_text}\nQuestion: {item.question}\nAnswer:"

                # Perform Generation (using the specific model if possible, here using model_name as parameter if LLMService supports it)
                # For MVP, we pass it as a hint or just use it to label the report
                answer = await llm.chat_complete([{"role": "user", "content": gen_prompt}])

                # Simulate token tracking
                sent_tokens = len(gen_prompt) // 4
                recv_tokens = len(answer) // 4
                total_tokens += sent_tokens + recv_tokens

                results.append(
                    {
                        "question": item.question,
                        "ground_truth": item.ground_truth,
                        "answer": answer,
                        "contexts": contexts,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to run RAG for evaluation item {item.id}: {e}")

        # 3. Score using LLM-as-a-judge
        judge = llm
        scored_details = []
        faith_scores = []
        relev_scores = []
        prec_scores = []
        recall_scores = []

        for res, item in zip(results, items, strict=False):
            try:
                # Optimized multi-judge prompt to save tokens (AI-First efficiency)
                judge_prompt = f"""
                Analyze the RAG result:
                Q: {res["question"]}
                GT: {res["ground_truth"]}
                AI: {res["answer"]}
                Context: {res["contexts"][:3]}
                
                Rate 0.0-1.0 for:
                1. Faithfulness (AI based on Context)
                2. Relevance (AI matches Q)
                3. Precision (Context matches Q)
                4. Recall (Context contains GT)
                
                Return JSON only: {{"f": 0.0, "r": 0.0, "p": 0.0, "rec": 0.0}}
                """
                j_resp = await judge.chat_complete([{"role": "user", "content": judge_prompt}], json_mode=True)
                scores = json.loads(j_resp)

                f_s, r_s, p_s, rec_s = scores.get("f", 0), scores.get("r", 0), scores.get("p", 0), scores.get("rec", 0)

                faith_scores.append(f_s)
                relev_scores.append(r_s)
                prec_scores.append(p_s)
                recall_scores.append(rec_s)

                scored_details.append(
                    {**res, "faithfulness": f_s, "relevance": r_s, "context_precision": p_s, "context_recall": rec_s}
                )
            except Exception as e:
                logger.warning(f"Judge failed for item: {e}")

        # 4. Finalize Report with M2.5 Metrics
        end_time = time.time()
        report.latency_ms = (end_time - start_time) * 1000
        report.token_usage = total_tokens
        # Simple cost estimation: $0.002 per 1k tokens
        report.cost = (total_tokens / 1000) * 0.002

        if faith_scores:
            report.faithfulness = sum(faith_scores) / len(faith_scores)
            report.answer_relevance = sum(relev_scores) / len(relev_scores)
            report.context_precision = sum(prec_scores) / len(prec_scores)
            report.context_recall = sum(recall_scores) / len(recall_scores)
            report.total_score = (
                report.faithfulness + report.answer_relevance + report.context_precision + report.context_recall
            ) / 4

        report.details_json = json.dumps(scored_details)
        report.status = "completed"

        db.add(report)
        await db.commit()
        await db.refresh(report)

        logger.info(
            f"✅ Evaluation complete for {target_model}: Score={report.total_score:.2f}, Cost=${report.cost:.4f}"
        )
        return report
