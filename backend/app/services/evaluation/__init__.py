"""
Evaluation Service — Unified RAG & Agent Quality Assessment.

Architecture (v2):
  - 独立 Grader 体系: 每个维度独立评估，避免认知负荷过重
  - 检索/生成解耦: 支持 L1 Retriever 独立评测 + L2 Generator 独立评测
  - 硬规则断言: RagAssertionGrader 集成到主流程
  - CoT 推理: 所有评分强制先推理再打分
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.llm import get_llm_service
from app.models.evaluation import EvaluationItem, EvaluationReport, EvaluationSet
from app.models.knowledge import DocumentChunk, KnowledgeBaseDocumentLink


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
            prompt = (
                "Based on the following text chunk, generate a realistic question and its definitive answer "
                "(ground truth).\n"
                "The question should be something a user would actually ask.\n"
                "The answer must be based ENTIRELY on the provided text.\n\n"
                "Format as JSON:\n"
                '{"question": "...", "answer": "..."}\n\n'
                f"Text Chunk:\n{chunk.content}"
            )

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
    async def run_evaluation(
        db: AsyncSession, set_id: str, model_name: str | None = None, apply_reflection: bool = False
    ) -> EvaluationReport:
        """
        Runs the RAGAS evaluation pipeline with independent graders (v2).

        Architecture:
          1. Retrieval: Get context for each question
          2. Generation: Get LLM response
          3. Independent Grading: Each dimension scored by its own specialized grader
          4. Hard Rule Assertion: RagAssertionGrader caps scores on violations
          5. Aggregate: Weighted composite score

        Changes from v1:
          - Each dimension uses an independent Grader with CoT reasoning
          - RagAssertionGrader integrated into main scoring pipeline
          - Grading results include reasoning and confidence
        """
        import asyncio
        import time
        from app.services.evaluation.metrics import (
            calculate_mrr, calculate_precision_at_k, calculate_recall_at_k,
            calculate_hit_rate, calculate_ndcg
        )
        from app.services.evaluation.bias_mitigation import BiasMitigationGrader

        from app.services.evaluation.graders import (
            ContextPrecisionGrader,
            ContextRecallGrader,
            CorrectnessGrader,
            FaithfulnessGrader,
            RelevanceGrader,
            InstructionFollowingGrader,
        )
        from app.services.evaluation.rag_assertion_grader import rag_assertion_grader

        start_time = time.time()

        target_model = model_name or "gpt-3.5-turbo"
        logger.info(f"🚀 Running evaluation (v2) for set {set_id} using model {target_model}")

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
        
        # New: L1 Metrics Accumulators
        k_values = [1, 3, 5, 10]
        metrics_by_k = {k: {"precision": [], "recall": [], "hit_rate": []} for k in k_values}
        mrr_scores = []
        ndcg_scores = {k: [] for k in k_values}

        for item in items:
            try:
                from app.models.knowledge import KnowledgeBase
                from app.services.retrieval.pipeline import RetrievalPipeline

                kb = await db.get(KnowledgeBase, eval_set.kb_id)
                if not kb:
                    continue

                pipeline = RetrievalPipeline()
                docs, _trace = await pipeline.run(item.question, collection_names=[kb.vector_collection])
                contexts = [doc.page_content for doc in docs]

                context_text = "\n\n".join(contexts)
                gen_prompt = (
                    "Use the context below to answer the question. "
                    "Cite sources using [1], [2] format.\n"
                    f"Context: {context_text}\n"
                    f"Question: {item.question}\n"
                    "Answer:"
                )

                answer = await llm.chat_complete([{"role": "user", "content": gen_prompt}])

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

                # NEW: Calculate L1 Metrics during retrieval
                if item.reference_context:
                    relevant_indices = []
                    binary_relevance = []
                    gold_text = item.reference_context.lower()
                    
                    for i, doc in enumerate(docs):
                        doc_text = doc.page_content.lower()
                        gold_words = set(gold_text.split())
                        doc_words = set(doc_text.split())
                        overlap_ratio = len(gold_words & doc_words) / max(len(gold_words), 1)
                        is_relevant = overlap_ratio > 0.35
                        
                        if is_relevant:
                            relevant_indices.append(i)
                            binary_relevance.append(1)
                        else:
                            binary_relevance.append(0)

                    for k in k_values:
                        metrics_by_k[k]["precision"].append(calculate_precision_at_k(relevant_indices, k))
                        metrics_by_k[k]["recall"].append(calculate_recall_at_k(relevant_indices, 1, k))
                        metrics_by_k[k]["hit_rate"].append(calculate_hit_rate(relevant_indices, k))
                        ndcg_scores[k].append(calculate_ndcg(binary_relevance[:k], k))
                    
                    mrr_scores.append(calculate_mrr(relevant_indices))
            except Exception as e:
                logger.error(f"Failed to run RAG for evaluation item {item.id}: {e}")

        # 2. Initialize independent graders
        faithfulness_grader = FaithfulnessGrader()
        relevance_grader = RelevanceGrader()
        correctness_grader = CorrectnessGrader()
        ctx_precision_grader = ContextPrecisionGrader()
        ctx_recall_grader = ContextRecallGrader()
        instruction_grader = InstructionFollowingGrader()

        # 3. Score each item with independent graders
        scored_details = []
        faith_scores = []
        relev_scores = []
        prec_scores = []
        recall_scores = []
        correct_scores = []
        sim_scores = []
        inst_scores = []
        bias_mitigator = BiasMitigationGrader() if apply_reflection else None

        for res_item in results:
            try:
                q = res_item["question"]
                a = res_item["answer"]
                gt = res_item["ground_truth"]
                ctxs = res_item["contexts"]

                # Run all graders in parallel for this item
                grade_tasks = [
                    faithfulness_grader.grade(question=q, answer=a, contexts=ctxs),
                    relevance_grader.grade(question=q, answer=a),
                    correctness_grader.grade(question=q, answer=a, ground_truth=gt),
                    ctx_precision_grader.grade(question=q, answer=a, contexts=ctxs),
                    ctx_recall_grader.grade(question=q, answer=a, ground_truth=gt, contexts=ctxs),
                    instruction_grader.grade(question=q, answer=a),
                ]

                grade_results = await asyncio.gather(*grade_tasks, return_exceptions=True)

                # Extract scores, handling failures gracefully
                f_result = grade_results[0] if not isinstance(grade_results[0], Exception) else None
                r_result = grade_results[1] if not isinstance(grade_results[1], Exception) else None
                acc_result = grade_results[2] if not isinstance(grade_results[2], Exception) else None
                p_result = grade_results[3] if not isinstance(grade_results[3], Exception) else None
                rec_result = grade_results[4] if not isinstance(grade_results[4], Exception) else None
                inst_result = grade_results[5] if not isinstance(grade_results[5], Exception) else None

                f_s = f_result.score if f_result else 0.0
                r_s = r_result.score if r_result else 0.0
                acc_s = acc_result.score if acc_result else 0.0
                p_s = p_result.score if p_result else 0.0
                rec_s = rec_result.score if rec_result else 0.0
                inst_s = inst_result.score if inst_result else 0.0

                # OPTIONAL: Bias Mitigation via Reflection
                if apply_reflection and bias_mitigator:
                    logger.info(f"🔍 Applying bias reflection to metrics for item...")
                    # Example: Reflect on faithfulness
                    f_ref = await bias_mitigator.reflected_grade("faithfulness", faithfulness_grader, 
                                                               question=q, answer=a, contexts=ctxs)
                    f_s = f_ref["final_score"]
                    # Reflect on instruction following
                    inst_ref = await bias_mitigator.reflected_grade("instruction_following", instruction_grader,
                                                                 question=q, answer=a)
                    inst_s = inst_ref["final_score"]

                # Semantic similarity: use average of faithfulness and correctness as proxy
                sim_s = round((f_s + acc_s) / 2, 3)

                # 4. Hard Rule Assertion — cap scores on violations
                context_text = "\n".join(ctxs) if ctxs else ""
                assertion_result = rag_assertion_grader.check(q, a, context_text)

                if not assertion_result.is_clean:
                    for violation in assertion_result.violations:
                        if violation.rule_id == "CITE-001":
                            f_s = min(f_s, violation.penalty)
                            logger.info(f"🚩 CITE-001: Faithfulness capped to {violation.penalty}")
                        elif violation.rule_id == "CITE-002":
                            acc_s = min(acc_s, violation.penalty)
                            logger.info(f"🚩 CITE-002: Correctness capped to {violation.penalty}")

                faith_scores.append(f_s)
                relev_scores.append(r_s)
                prec_scores.append(p_s)
                recall_scores.append(rec_s)
                correct_scores.append(acc_s)
                sim_scores.append(sim_s)
                inst_scores.append(inst_s)

                scored_details.append(
                    {
                        **res_item,
                        "faithfulness": f_s,
                        "relevance": r_s,
                        "context_precision": p_s,
                        "context_recall": rec_s,
                        "answer_correctness": acc_s,
                        "semantic_similarity": sim_s,
                        "instruction_following": inst_s,
                        "assertion_violations": [
                            {"rule": v.rule_id, "desc": v.description}
                            for v in assertion_result.violations
                        ],
                        "grader_reasoning": {
                            "faithfulness": f_result.reasoning if f_result else "grader failed",
                            "relevance": r_result.reasoning if r_result else "grader failed",
                            "correctness": acc_result.reasoning if acc_result else "grader failed",
                            "context_precision": p_result.reasoning if p_result else "grader failed",
                            "context_recall": rec_result.reasoning if rec_result else "grader failed",
                            "instruction_following": inst_result.reasoning if inst_result else "grader failed",
                        },
                        "grader_confidence": {
                            "faithfulness": f_result.confidence if f_result else "low",
                            "relevance": r_result.confidence if r_result else "low",
                            "correctness": acc_result.confidence if acc_result else "low",
                            "context_precision": p_result.confidence if p_result else "low",
                            "context_recall": rec_result.confidence if rec_result else "low",
                        },
                    }
                )

                # ─── HITL: Auto-record BadCases ───
                # Threshold: Weighted score for this specific item < 0.5
                item_score = (f_s*0.2 + acc_s*0.4 + r_s*0.2 + inst_s*0.2)
                if item_score < 0.5:
                    from app.models.evaluation import BadCase
                    case = BadCase(
                        report_id=report.id,
                        question=q,
                        bad_answer=a,
                        reason=f"Auto-flagged: score={item_score:.2f}",
                        context_snapshot=context_text[:2000],  # Save sample of context
                        ai_insight=(
                            f"System Alert: Faithfulness={f_s}. "
                            f"Reasoning: {f_result.reasoning if f_result else 'N/A'}. "
                            "Human: Please verify if the context actually supports the answer."
                        )
                    )
                    db.add(case)

            except Exception as e:
                logger.warning(f"Grading failed for item: {e}")

        # 5. Finalize Report
        end_time = time.time()
        report.latency_ms = (end_time - start_time) * 1000
        report.token_usage = total_tokens
        report.cost = (total_tokens / 1000) * 0.002

        if faith_scores:
            report.faithfulness = round(sum(faith_scores) / len(faith_scores), 3)
            report.answer_relevance = round(sum(relev_scores) / len(relev_scores), 3)
            report.context_precision = round(sum(prec_scores) / len(prec_scores), 3)
            report.context_recall = round(sum(recall_scores) / len(recall_scores), 3)
            report.answer_correctness = round(sum(correct_scores) / len(correct_scores), 3)
            report.semantic_similarity = round(sum(sim_scores) / len(sim_scores), 3)
            report.instruction_following = round(sum(inst_scores) / len(inst_scores), 3)

            # L1 Integration - Calculate aggregate L1 metrics for the report
            report.mrr = round(sum(mrr_scores) / len(mrr_scores), 3) if mrr_scores else 0.0
            # Hit rate and NDCG are usually @K. For the summary, we store @5.
            report.hit_rate = round(sum(metrics_by_k[5]["hit_rate"]) / len(items), 3) if items else 0.0
            report.ndcg = round(sum(ndcg_scores[5]) / len(items), 3) if items else 0.0

            report.total_score = round(
                report.faithfulness * 0.15 +
                report.answer_relevance * 0.1 +
                report.context_precision * 0.1 +
                report.context_recall * 0.1 +
                report.answer_correctness * 0.25 +
                report.semantic_similarity * 0.2 +
                (sum(inst_scores)/len(inst_scores) if inst_scores else 0) * 0.1,
                3,
            )

        report.details_json = json.dumps(scored_details, ensure_ascii=False)
        report.status = "completed"

        db.add(report)
        await db.commit()
        await db.refresh(report)

        logger.info(
            f"✅ Evaluation (v2) complete for {target_model}: "
            f"Score={report.total_score:.3f}, Cost=${report.cost:.4f}"
        )
        return report


    # ─── L1: Retriever 独立评测 ──────────────────────────────────────────────

    @staticmethod
    async def evaluate_retriever(
        db: AsyncSession,
        set_id: str,
        k_values: List[int] = [1, 3, 5, 10],
    ) -> dict:
        """
        L1 Retriever 独立评测 — 脱离生成环节，单独压测召回能力 (Refined v2).

        Returns multi-K metrics for Precision, Recall, Hit Rate, MRR, and NDCG.
        """
        from app.models.knowledge import KnowledgeBase
        from app.services.retrieval.pipeline import RetrievalPipeline
        from app.services.evaluation.metrics import (
            calculate_mrr, calculate_precision_at_k, calculate_recall_at_k,
            calculate_hit_rate, calculate_ndcg
        )

        max_k = max(k_values)
        logger.info(f"🔍 [L1] Running Deep Retriever evaluation for set {set_id} (Max K={max_k})")

        eval_set = await db.get(EvaluationSet, set_id)
        if not eval_set:
            raise ValueError("Evaluation set not found")

        stmt = select(EvaluationItem).where(EvaluationItem.set_id == set_id)
        res = await db.execute(stmt)
        items = res.scalars().all()

        kb = await db.get(KnowledgeBase, eval_set.kb_id)
        if not kb:
            raise ValueError("Knowledge base not found")

        pipeline = RetrievalPipeline()
        
        # Accumulators for all items
        metrics_by_k = {k: {"precision": [], "recall": [], "hit_rate": []} for k in k_values}
        mrr_scores = []
        ndcg_scores = {k: [] for k in k_values}

        for item in items:
            if not item.reference_context:
                continue

            try:
                docs, _trace = await pipeline.run(
                    item.question,
                    collection_names=[kb.vector_collection],
                    top_k=max_k,
                )

                # Relevancy Detection: Using a combination of semantic similarity proxy and keyword overlap
                # In a production system, this should be a Cross-Encoder or a fast LLM check.
                relevant_indices = []
                binary_relevance = [] # For NDCG

                gold_text = item.reference_context.lower()
                
                for i, doc in enumerate(docs):
                    doc_text = doc.page_content.lower()
                    
                    # Robust relevancy check:
                    # 1. Lexical overlap (Jaccard-like)
                    gold_words = set(gold_text.split())
                    doc_words = set(doc_text.split())
                    overlap_ratio = len(gold_words & doc_words) / max(len(gold_words), 1)
                    
                    # 2. Heuristic: Is the document content a substantial part of the reference or vice versa?
                    is_relevant = overlap_ratio > 0.35 # Threshold
                    
                    if is_relevant:
                        relevant_indices.append(i)
                        binary_relevance.append(1)
                    else:
                        binary_relevance.append(0)

                # Calculate metrics for each K
                for k in k_values:
                    metrics_by_k[k]["precision"].append(calculate_precision_at_k(relevant_indices, k))
                    # Note: total_relevant is assumed to be 1 for testsets generated from single chunks
                    metrics_by_k[k]["recall"].append(calculate_recall_at_k(relevant_indices, 1, k))
                    metrics_by_k[k]["hit_rate"].append(calculate_hit_rate(relevant_indices, k))
                    ndcg_scores[k].append(calculate_ndcg(binary_relevance[:k], k))

                # Global MRR (based on max_k)
                mrr_scores.append(calculate_mrr(relevant_indices))

            except Exception as e:
                logger.error(f"[L1] Retriever eval failed for item {item.id}: {e}")

        # Final Aggregation
        summary = {
            "level": "L1",
            "set_id": set_id,
            "items_count": len(items),
            "mrr": round(sum(mrr_scores) / len(mrr_scores), 3) if mrr_scores else 0.0,
            "metrics_at_k": {}
        }

        for k in k_values:
            summary["metrics_at_k"][f"k_{k}"] = {
                "precision": round(sum(metrics_by_k[k]["precision"]) / len(items), 3) if items else 0.0,
                "recall": round(sum(metrics_by_k[k]["recall"]) / len(items), 3) if items else 0.0,
                "hit_rate": round(sum(metrics_by_k[k]["hit_rate"]) / len(items), 3) if items else 0.0,
                "ndcg": round(sum(ndcg_scores[k]) / len(items), 3) if items else 0.0,
            }

        logger.info(f"✅ [L1] Deep Retriever eval complete. MRR={summary['mrr']}")
        return summary

    # ─── L2: Generator 独立评测 ──────────────────────────────────────────────

    @staticmethod
    async def evaluate_generator(
        db: AsyncSession,
        set_id: str,
    ) -> dict:
        """
        L2 Generator 独立评测 — 注入标准参考文档，消除检索噪音。

        直接将 EvaluationItem.reference_context 作为上下文注入 LLM，
        纯测 LLM 的语义总结与表达能力。
        """
        from app.services.evaluation.graders import (
            CorrectnessGrader,
            FaithfulnessGrader,
        )

        logger.info(f"✍️ [L2] Running Generator evaluation for set {set_id}")

        eval_set = await db.get(EvaluationSet, set_id)
        if not eval_set:
            raise ValueError("Evaluation set not found")

        stmt = select(EvaluationItem).where(EvaluationItem.set_id == set_id)
        res = await db.execute(stmt)
        items = res.scalars().all()

        llm = get_llm_service()
        faithfulness_grader = FaithfulnessGrader()
        correctness_grader = CorrectnessGrader()

        faith_scores = []
        correct_scores = []

        for item in items:
            if not item.reference_context:
                continue

            try:
                # 注入标准上下文（不经过检索）
                gen_prompt = (
                    "Use ONLY the context below to answer the question. "
                    "Do not use any prior knowledge.\n"
                    f"Context: {item.reference_context}\n"
                    f"Question: {item.question}\n"
                    "Answer:"
                )
                answer = await llm.chat_complete([{"role": "user", "content": gen_prompt}])

                # 评估忠实度和正确性
                f_result = await faithfulness_grader.grade(
                    question=item.question,
                    answer=answer,
                    contexts=[item.reference_context],
                )
                acc_result = await correctness_grader.grade(
                    question=item.question,
                    answer=answer,
                    ground_truth=item.ground_truth,
                )

                faith_scores.append(f_result.score)
                correct_scores.append(acc_result.score)

            except Exception as e:
                logger.error(f"[L2] Generator eval failed for item {item.id}: {e}")

        result = {
            "level": "L2",
            "type": "generator",
            "set_id": set_id,
            "items_evaluated": len(faith_scores),
            "faithfulness": round(sum(faith_scores) / len(faith_scores), 3) if faith_scores else 0.0,
            "answer_correctness": round(sum(correct_scores) / len(correct_scores), 3) if correct_scores else 0.0,
        }

        logger.info(
            f"✅ [L2] Generator eval complete: "
            f"Faithfulness={result['faithfulness']}, "
            f"Correctness={result['answer_correctness']}"
        )
        return result

    @staticmethod
    async def promote_bad_case_to_testset(db: AsyncSession, case_id: str, set_name: str = "HITL_Evolution_Set") -> EvaluationItem:
        """
        Promotes a manually corrected BadCase into a permanent EvaluationItem.
        This closes the HITL loop: Feedback -> Correction -> Benchmark.
        """
        from sqlmodel import select
        from app.models.evaluation import EvaluationSet, EvaluationItem, BadCase

        # 1. Fetch BadCase
        case = await db.get(BadCase, case_id)
        if not case or not case.expected_answer:
            raise ValueError("BadCase not found or missing expected_answer")

        # 2. Get or create the Evolution Set
        stmt = select(EvaluationSet).where(EvaluationSet.name == set_name)
        res = await db.execute(stmt)
        eval_set = res.scalars().first()
        
        if not eval_set:
            eval_set = EvaluationSet(name=set_name, description="Automatically generated from human-corrected Bad Cases.")
            # Default to a global KB or no KB if not applicable
            db.add(eval_set)
            await db.commit()
            await db.refresh(eval_set)

        # 3. Create EvaluationItem
        item = EvaluationItem(
            set_id=eval_set.id,
            question=case.question,
            ground_truth=case.expected_answer,
            category="hitl_correction",
            difficulty=4
        )
        db.add(item)
        
        # 4. Update Case Status
        case.status = "added_to_dataset"
        db.add(case)
        
        await db.commit()
        await db.refresh(item)
        
        logger.info(f"🚀 [HITL] Promoted BadCase {case_id} to EvaluationSet {set_name}")
        return item
