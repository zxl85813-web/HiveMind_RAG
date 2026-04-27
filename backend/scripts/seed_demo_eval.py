"""
Seed script for comprehensive evaluation demo data.
Seeds: KBs, Testsets, Evaluation Reports (multi-model), Bad Cases.

Usage:
    cd backend
    python -m scripts.seed_demo_eval
"""

# ruff: noqa: E501

import asyncio
import json
import random
import sys
import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("seed_demo_eval")
t_logger = get_trace_logger("scripts.demo_seed")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

from app.core.database import async_session_factory
from app.models.chat import User
from app.models.evaluation import BadCase, EvaluationItem, EvaluationReport, EvaluationSet
from app.models.knowledge import KnowledgeBase


# ============================================================
#  Realistic QA Pairs — Finance KB
# ============================================================
FINANCE_QA = [
    {
        "q": "研发费用的加计扣除比例是多少?",
        "gt": "根据2023年新规,符合条件的研发费用加计扣除比例已统一提高至100%。企业开展研发活动中实际发生的研发费用,未形成无形资产计入当期损益的,可按照实际发生额的100%在税前加计扣除。",
        "ctx": "《国家税务总局关于优化预缴申报研发费用加计扣除政策的公告》:将研发费用税前加计扣除比例统一提高至100%,适用于除烟草制造业等负面清单以外的所有行业。",
    },
    {
        "q": "差旅补助是否需要缴纳个人所得税?",
        "gt": "合理的差旅补贴和误餐补助不属于工资薪金性质的补贴,不征收个人所得税。但超出合理标准的部分需要按照工资薪金所得缴纳个税。",
        "ctx": "《个人所得税法实施条例》第十三条:个人因公务出差取得的差旅费津贴、误餐补助,不属于纳税人本人工资薪金所得项目的收入,不征税。",
    },
    {
        "q": "企业固定资产折旧的最低年限分别是多少?",
        "gt": "房屋建筑物20年,飞机火车轮船设备10年,与生产经营相关的器具工具5年,电子设备3年。",
        "ctx": "《企业所得税法实施条例》第六十条规定了各类固定资产计算折旧的最低年限。",
    },
    {
        "q": "小型微利企业所得税优惠政策是什么?",
        "gt": "对年应纳税所得额不超过300万元的小型微利企业,减按25%计入应纳税所得额,按20%的税率缴纳企业所得税,实际税负率为5%。",
        "ctx": "《财政部 税务总局关于小微企业和个体工商户所得税优惠政策的公告》2023年第6号。",
    },
    {
        "q": "增值税留抵退税政策适用于哪些行业?",
        "gt": "2022年起,增值税留抵退税政策扩大至所有行业。符合条件的小微企业 and 制造业等6个行业可以申请一次性退还存量留抵税额,并按月退还增量留抵税额。",
        "ctx": "《财政部 税务总局关于进一步加大增值税期末留抵退税政策实施力度的公告》。",
    },
    {
        "q": "企业年金缴费的税前扣除标准是多少?",
        "gt": "企业缴费部分在不超过职工工资总额5%标准内的部分,在计算企业所得税应纳税所得额时准予扣除。个人缴费不超过本人缴费工资计税基数4%的部分,暂从个人当期的应纳税所得额中扣除。",
        "ctx": "《企业年金试行办法》及《关于企业年金 职业年金个人所得税有关问题的通知》。",
    },
    {
        "q": "跨境电商综合税率如何计算?",
        "gt": "跨境电商零售进口商品的综合税率=关税×0%+增值税×70%+消费税×70%。单次限额5000元,年度限额26000元以内可享受优惠税率。",
        "ctx": "《关于跨境电子商务零售进口税收政策的通知》(财关税〔2016〕18号)。",
    },
    {
        "q": "合同印花税的税率是多少?",
        "gt": "2022年7月1日起施行的《印花税法》中,买卖合同税率为价款的万分之三,借款合同为借款金额的万分之零点五,技术合同为价款的万分之三,财产租赁合同为租金的千分之一。",
        "ctx": "《中华人民共和国印花税法》(2022年7月1日起施行)。",
    },
]

# ============================================================
#  Realistic QA Pairs — HR Policy KB
# ============================================================
HR_QA = [
    {
        "q": "员工试用期最长可以设置多久?",
        "gt": "劳动合同期限三个月以上不满一年的,试用期不得超过一个月；一年以上不满三年的,试用期不得超过二个月；三年以上固定期限和无固定期限的,试用期不得超过六个月。",
        "ctx": "《劳动合同法》第十九条。",
    },
    {
        "q": "公司解除劳动合同需要提前多少天通知?",
        "gt": "用人单位提前三十日以书面形式通知劳动者本人或者额外支付劳动者一个月工资后,可以解除劳动合同。经济性裁员需要提前三十日向工会或者全体职工说明情况。",
        "ctx": "《劳动合同法》第四十条、第四十一条。",
    },
    {
        "q": "年假天数如何计算?",
        "gt": "职工累计工作已满1年不满10年的,年休假5天；已满10年不满20年的,年休假10天；已满20年的,年休假15天。国家法定休假日和休息日不计入年休假的假期。",
        "ctx": "《企业职工带薪年休假实施办法》。",
    },
    {
        "q": "产假法定天数是多少?",
        "gt": "女职工生育享受98天产假,其中产前15天可以休假。难产的增加15天产假。生育多胞胎的,每多一个婴儿增加15天产假。各省市可能有额外奖励假期。",
        "ctx": "《女职工劳动保护特别规定》第七条。",
    },
    {
        "q": "加班费的计算标准是什么?",
        "gt": "工作日加班按不低于工资的150%支付；休息日加班又不能安排补休的,按不低于工资的200%支付；法定休假日加班的,按不低于工资的300%支付。",
        "ctx": "《劳动法》第四十四条。",
    },
    {
        "q": "员工医疗期如何确定?",
        "gt": "实际工作年限10年以下、在本单位工作年限5年以下的为3个月；5年以上的为6个月。实际工作年限10年以上、在本单位5年以下的为6个月；5年以上10年以下的为9个月；10年以上15年以下的为12个月；15年以上20年以下的为18个月；20年以上的为24个月。",
        "ctx": "《企业职工患病或非因工负伤医疗期规定》。",
    },
    {
        "q": "竞业限制补偿金不低于多少?",
        "gt": "用人单位按月给予劳动者经济补偿,补偿金不低于劳动者在劳动合同解除或终止前十二个月平均工资的30%。若不足当地最低工资标准,按最低工资标准支付。竞业限制期限不得超过二年。",
        "ctx": "《最高人民法院关于审理劳动争议案件适用法律问题的解释(一)》。",
    },
]


# ============================================================
#  Model Configurations for Arena
# ============================================================
MODEL_CONFIGS = {
    "claude-4.6-thinking": {
        "latency_range": (3500, 6500),
        "cost_range": (0.08, 0.15),
        "token_range": (1500, 4000),
        "score_range": (0.94, 0.99),
        "faith_range": (0.95, 1.0),
        "relev_range": (0.94, 1.0),
        "elo": 1504
    },
    "gemini-3.1-pro": {
        "latency_range": (1200, 2500),
        "cost_range": (0.03, 0.07),
        "token_range": (1000, 3000),
        "score_range": (0.91, 0.97),
        "faith_range": (0.90, 0.98),
        "relev_range": (0.92, 0.98),
        "elo": 1492
    },
    "gpt-5.4-high": {
        "latency_range": (1800, 3200),
        "cost_range": (0.05, 0.12),
        "token_range": (1200, 3500),
        "score_range": (0.89, 0.96),
        "faith_range": (0.88, 0.97),
        "relev_range": (0.90, 0.96),
        "elo": 1484
    },
    "grok-4.20-beta": {
        "latency_range": (1000, 2200),
        "cost_range": (0.02, 0.05),
        "token_range": (800, 2500),
        "score_range": (0.86, 0.94),
        "faith_range": (0.85, 0.95),
        "relev_range": (0.88, 0.95),
        "elo": 1486
    },
    "deepseek-v3.2": {
        "latency_range": (300, 700),
        "cost_range": (0.0005, 0.002),
        "token_range": (400, 1500),
        "score_range": (0.82, 0.92),
        "faith_range": (0.80, 0.91),
        "relev_range": (0.84, 0.93),
        "elo": 1465
    },
}


# ============================================================
#  Model-specific answer generators (simulate quality)
# ============================================================
GOOD_ANSWER_TEMPLATES = {
    "claude-4.6-thinking": "根据最新政策规定,{gt_short} 这一标准适用于大多数场景。深度思考建议：关注长效合规性。",
    "gemini-3.1-pro": "综合法律法规分析,{gt_short} 建议在实务操作中注意相关部门的准入要求。",
    "gpt-5.4-high": "{gt_short} 此外，请注意该解读仅供参考，不构成正式法律建议。",
    "grok-4.20-beta": "实时检索显示,{gt_short} 建议根据具体城市落地政策进一步对齐。",
    "deepseek-v3.2": "{gt_short_partial} 本地优化结果显示该项执行效率最高。",
}


BAD_ANSWER_TEMPLATES = [
    "这个取决于具体情况,建议咨询专业人士。",
    "根据一般经验,可能需要进一步确认。",
    "抱歉,我对这个问题不太确定,请以官方文件为准。",
    "这个问题比较复杂,不同地区可能有不同规定。",
]


def _rand(low, high):
    return round(random.uniform(low, high), 4)


def _gen_detail(qa_pairs, model_name, conf):
    """Generate detailed QA eval results for a report."""
    details = []
    for qa in qa_pairs:
        faith = _rand(*conf["faith_range"])
        relev = _rand(*conf["relev_range"])
        ctx_prec = _rand(max(0.3, faith - 0.15), min(1.0, faith + 0.1))
        ctx_recall = _rand(max(0.3, relev - 0.1), min(1.0, relev + 0.05))

        gt_short = qa["gt"][:60]
        gt_short_partial = qa["gt"][:35]

        if faith > 0.65:
            tpl = GOOD_ANSWER_TEMPLATES.get(model_name, "{gt_short}")
            answer = tpl.format(gt_short=gt_short, gt_short_partial=gt_short_partial)
        else:
            answer = random.choice(BAD_ANSWER_TEMPLATES)

        details.append(
            {
                "question": qa["q"],
                "ground_truth": qa["gt"],
                "answer": answer,
                "faithfulness": round(faith, 2),
                "relevance": round(relev, 2),
                "context_precision": round(ctx_prec, 2),
                "context_recall": round(ctx_recall, 2),
                "contexts": [qa["ctx"][:80] + "..."],
            }
        )
    return details


async def seed_eval_data():
    t_logger.info("🚀 Starting comprehensive evaluation data seeding...", action="seed_start")
    async with async_session_factory() as session:
        # ── 0. Check mock user ──
        user = await session.get(User, "mock-user-001")
        if not user:
            t_logger.info("Mock user not found. Creating default 'mock-user-001'...")
            user = User(
                id="mock-user-001",
                username="eval_judge",
                email="eval@hivemind.ai",
                hashed_password="fake_hash_for_test",
                role="admin"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # ── 1. Create Knowledge Bases ──
        kb_finance_id = "kb-demo-smart-finance"
        kb_hr_id = "kb-demo-hr-policy"

        existing_kb1 = await session.get(KnowledgeBase, kb_finance_id)
        if not existing_kb1:
            kb1 = KnowledgeBase(
                id=kb_finance_id,
                name="智能财务专家知识库",
                description="包含 2024-2025 年度财务准则、税务合规及预算管理规范。涵盖企业所得税、增值税、印花税等核心税种。",
                owner_id=user.id,
                vector_collection="demo_finance_collection",
                created_at=datetime.utcnow() - timedelta(days=15),
            )
            session.add(kb1)
            t_logger.info("✅ Created KB: 智能财务专家知识库")

        existing_kb2 = await session.get(KnowledgeBase, kb_hr_id)
        if not existing_kb2:
            kb2 = KnowledgeBase(
                id=kb_hr_id,
                name="HR 政策与劳动法知识库",
                description="企业 HR 常见问题、劳动法规、薪酬福利政策,覆盖劳动合同法、社保公积金等内容。",
                owner_id=user.id,
                vector_collection="demo_hr_collection",
                created_at=datetime.utcnow() - timedelta(days=12),
            )
            session.add(kb2)
            t_logger.info("✅ Created KB: HR 政策与劳动法知识库")

        # ── 2. Create Testsets ──
        set_finance_id = "evalset-finance-core"
        set_hr_id = "evalset-hr-core"
        set_finance_adv_id = "evalset-finance-advanced"

        for set_id, kb_id, name, desc, days_ago in [
            (
                set_finance_id,
                kb_finance_id,
                "Q4 财务合规性评估测试集",
                "针对财务报表审计、税务扣除项、印花税等核心财务知识的专项测试集。共8组QA对。",
                10,
            ),
            (
                set_hr_id,
                kb_hr_id,
                "HR 劳动法应答质量评估集",
                "覆盖试用期、年假、产假、加班、竞业限制等常见 HR 问题。共7组QA对。",
                8,
            ),
            (
                set_finance_adv_id,
                kb_finance_id,
                "高级财务场景综合测试集",
                "综合测试跨境电商税率、企业年金等进阶财务场景。",
                5,
            ),
        ]:
            existing = await session.get(EvaluationSet, set_id)
            if not existing:
                session.add(
                    EvaluationSet(
                        id=set_id,
                        kb_id=kb_id,
                        name=name,
                        description=desc,
                        created_at=datetime.utcnow() - timedelta(days=days_ago),
                    )
                )
                t_logger.info(f"  📝 Testset: {name}")

        # ── 3. Create Evaluation Items ──
        from sqlmodel import select

        existing_items = await session.execute(select(EvaluationItem).limit(1))
        if not existing_items.scalars().first():
            items = []
            for qa in FINANCE_QA:
                items.append(
                    EvaluationItem(
                        id=str(uuid.uuid4()),
                        set_id=set_finance_id,
                        question=qa["q"],
                        ground_truth=qa["gt"],
                        reference_context=qa["ctx"],
                    )
                )
            for qa in HR_QA:
                items.append(
                    EvaluationItem(
                        id=str(uuid.uuid4()),
                        set_id=set_hr_id,
                        question=qa["q"],
                        ground_truth=qa["gt"],
                        reference_context=qa["ctx"],
                    )
                )
            # Advanced set reuses some finance QA
            for qa in FINANCE_QA[5:]:
                items.append(
                    EvaluationItem(
                        id=str(uuid.uuid4()),
                        set_id=set_finance_adv_id,
                        question=qa["q"],
                        ground_truth=qa["gt"],
                        reference_context=qa["ctx"],
                    )
                )
            session.add_all(items)
            t_logger.info(f"  ✅ Created {len(items)} evaluation items")

        # ── 4. Create Evaluation Reports (Multi-Model Arena) ──
        existing_reports = await session.execute(select(EvaluationReport).limit(1))
        if not existing_reports.scalars().first():
            reports = []

            # Each model gets 2 reports on finance, 1 on HR, some get advanced too
            for model_name, conf in MODEL_CONFIGS.items():
                # --- Finance KB Report #1 (older) ---
                details_1 = _gen_detail(FINANCE_QA, model_name, conf)
                avg_faith_1 = sum(d["faithfulness"] for d in details_1) / len(details_1)
                avg_relev_1 = sum(d["relevance"] for d in details_1) / len(details_1)
                avg_prec_1 = sum(d["context_precision"] for d in details_1) / len(details_1)
                avg_recall_1 = sum(d["context_recall"] for d in details_1) / len(details_1)
                
                # New Metrics calculation
                avg_inst_1 = _rand(0.7, 0.99) if "thinking" in model_name else _rand(0.6, 0.9)
                avg_hit_1 = _rand(0.8, 0.98)
                avg_mrr_1 = _rand(0.6, 0.9)
                avg_ndcg_1 = _rand(0.65, 0.92)
                
                score_1 = (avg_faith_1 + avg_relev_1 + avg_prec_1 + avg_recall_1 + avg_inst_1) / 5

                reports.append(
                    EvaluationReport(
                        id=str(uuid.uuid4()),
                        set_id=set_finance_id,
                        kb_id=kb_finance_id,
                        model_name=model_name,
                        faithfulness=round(avg_faith_1, 4),
                        answer_relevance=round(avg_relev_1, 4),
                        context_precision=round(avg_prec_1, 4),
                        context_recall=round(avg_recall_1, 4),
                        # Injecting new metrics
                        instruction_following=round(avg_inst_1, 4),
                        hit_rate=round(avg_hit_1, 4),
                        mrr=round(avg_mrr_1, 4),
                        ndcg=round(avg_ndcg_1, 4),
                        
                        total_score=round(score_1, 4),
                        latency_ms=round(_rand(*conf["latency_range"]), 1),
                        cost=round(_rand(*conf["cost_range"]), 4),
                        token_usage=random.randint(*conf["token_range"]),
                        details_json=json.dumps(details_1, ensure_ascii=False),
                        status="completed",
                        created_at=datetime.utcnow() - timedelta(days=7, hours=random.randint(0, 23)),
                    )
                )

                # --- HR KB Report ---
                details_hr = _gen_detail(HR_QA, model_name, conf)
                avg_faith_hr = sum(d["faithfulness"] for d in details_hr) / len(details_hr)
                avg_relev_hr = sum(d["relevance"] for d in details_hr) / len(details_hr)
                avg_prec_hr = sum(d["context_precision"] for d in details_hr) / len(details_hr)
                avg_recall_hr = sum(d["context_recall"] for d in details_hr) / len(details_hr)
                
                avg_inst_hr = _rand(0.7, 0.99) if "thinking" in model_name else _rand(0.6, 0.9)
                avg_hit_hr = _rand(0.8, 0.98)
                avg_mrr_hr = _rand(0.6, 0.9)
                avg_ndcg_hr = _rand(0.65, 0.92)
                
                score_hr = (avg_faith_hr + avg_relev_hr + avg_prec_hr + avg_recall_hr + avg_inst_hr) / 5

                reports.append(
                    EvaluationReport(
                        id=str(uuid.uuid4()),
                        set_id=set_hr_id,
                        kb_id=kb_hr_id,
                        model_name=model_name,
                        faithfulness=round(avg_faith_hr, 4),
                        answer_relevance=round(avg_relev_hr, 4),
                        context_precision=round(avg_prec_hr, 4),
                        context_recall=round(avg_recall_hr, 4),
                        # Injecting new metrics
                        instruction_following=round(avg_inst_hr, 4),
                        hit_rate=round(avg_hit_hr, 4),
                        mrr=round(avg_mrr_hr, 4),
                        ndcg=round(avg_ndcg_hr, 4),
                        
                        total_score=round(score_hr, 4),
                        latency_ms=round(_rand(*conf["latency_range"]), 1),
                        cost=round(_rand(*conf["cost_range"]), 4),
                        token_usage=random.randint(*conf["token_range"]),
                        details_json=json.dumps(details_hr, ensure_ascii=False),
                        status="completed",
                        created_at=datetime.utcnow() - timedelta(days=5, hours=random.randint(0, 23)),
                    )
                )

                # --- Finance KB Report #2 (recent) ---
                details_2 = _gen_detail(FINANCE_QA, model_name, conf)
                avg_faith_2 = sum(d["faithfulness"] for d in details_2) / len(details_2)
                avg_relev_2 = sum(d["relevance"] for d in details_2) / len(details_2)
                avg_prec_2 = sum(d["context_precision"] for d in details_2) / len(details_2)
                avg_recall_2 = sum(d["context_recall"] for d in details_2) / len(details_2)
                
                avg_inst_2 = _rand(0.7, 0.99) if "thinking" in model_name else _rand(0.6, 0.9)
                avg_hit_2 = _rand(0.8, 0.98)
                avg_mrr_2 = _rand(0.6, 0.9)
                avg_ndcg_2 = _rand(0.65, 0.92)
                
                score_2 = (avg_faith_2 + avg_relev_2 + avg_prec_2 + avg_recall_2 + avg_inst_2) / 5

                reports.append(
                    EvaluationReport(
                        id=str(uuid.uuid4()),
                        set_id=set_finance_id,
                        kb_id=kb_finance_id,
                        model_name=model_name,
                        faithfulness=round(avg_faith_2, 4),
                        answer_relevance=round(avg_relev_2, 4),
                        context_precision=round(avg_prec_2, 4),
                        context_recall=round(avg_recall_2, 4),
                        # Injecting new metrics
                        instruction_following=round(avg_inst_2, 4),
                        hit_rate=round(avg_hit_2, 4),
                        mrr=round(avg_mrr_2, 4),
                        ndcg=round(avg_ndcg_2, 4),
                        
                        total_score=round(score_2, 4),
                        latency_ms=round(_rand(*conf["latency_range"]), 1),
                        cost=round(_rand(*conf["cost_range"]), 4),
                        token_usage=random.randint(*conf["token_range"]),
                        details_json=json.dumps(details_2, ensure_ascii=False),
                        status="completed",
                        created_at=datetime.utcnow() - timedelta(days=2, hours=random.randint(0, 23)),
                    )
                )


            session.add_all(reports)
            t_logger.info(f"  📊 Created {len(reports)} evaluation reports across {len(MODEL_CONFIGS)} models")

        # ── 5. Create Bad Cases ──
        existing_bc = await session.execute(select(BadCase).limit(1))
        if not existing_bc.scalars().first():
            bad_cases = [
                BadCase(
                    id=str(uuid.uuid4()),
                    question="研发费用加计扣除的比例是多少?",
                    bad_answer="一般企业的研发费用可以按照50%进行加计扣除。",
                    expected_answer="根据2023年新规,符合条件的研发费用加计扣除比例已统一提高至100%。",
                    reason="数据过时 — 引用了旧版本政策(2018年前),最新政策已调整为100%",
                    status="reviewed",
                    created_at=datetime.utcnow() - timedelta(days=6),
                ),
                BadCase(
                    id=str(uuid.uuid4()),
                    question="小微企业所得税税率是多少?",
                    bad_answer="小微企业按照25%的标准税率缴纳企业所得税。",
                    expected_answer="小型微利企业减按25%计入应纳税所得额,按20%税率缴纳,实际税负率为5%。",
                    reason="幻觉回答 — 混淆了标准税率和优惠税率,未提及减计优惠政策",
                    status="pending",
                    created_at=datetime.utcnow() - timedelta(days=5),
                ),
                BadCase(
                    id=str(uuid.uuid4()),
                    question="员工试用期最长能设置多久?",
                    bad_answer="试用期一般为3个月。",
                    expected_answer="根据合同期限不同:不满一年的试用期不超过1个月,1-3年的不超过2个月,3年以上的不超过6个月。",
                    reason="回答不完整 — 只给出了一个固定值,没有根据合同期限分类说明",
                    status="pending",
                    created_at=datetime.utcnow() - timedelta(days=4),
                ),
                BadCase(
                    id=str(uuid.uuid4()),
                    question="加班费怎么算?",
                    bad_answer="加班费按基本工资的两倍计算。",
                    expected_answer="工作日加班150%,休息日200%(不能补休时),法定节假日300%。",
                    reason="事实性错误 — 统一按200%计算是错误的,应区分工作日/休息日/法定节假日三种场景",
                    status="fixed",
                    created_at=datetime.utcnow() - timedelta(days=3),
                ),
                BadCase(
                    id=str(uuid.uuid4()),
                    question="跨境电商进口怎么交税?",
                    bad_answer="跨境电商进口需要全额缴纳关税和增值税。",
                    expected_answer="跨境电商零售进口关税税率为0%,增值税和消费税按70%征收,单次限额5000元,年度限额26000元。",
                    reason="严重失实 — 忽略了跨境电商专属优惠政策,按一般贸易方式回答",
                    status="added_to_dataset",
                    created_at=datetime.utcnow() - timedelta(days=2),
                ),
                BadCase(
                    id=str(uuid.uuid4()),
                    question="竞业限制的补偿金标准是什么?",
                    bad_answer="竞业限制没有强制的补偿金标准。",
                    expected_answer="不低于劳动者解除前12个月平均工资的30%,且不低于当地最低工资标准,期限不超过2年。",
                    reason="法律知识错误 — 最高院司法解释已有明确规定,不是无标准",
                    status="reviewed",
                    created_at=datetime.utcnow() - timedelta(days=1),
                ),
                BadCase(
                    id=str(uuid.uuid4()),
                    question="年假怎么算?在公司工作了8年有几天?",
                    bad_answer="年假统一为10天。",
                    expected_answer="工龄1-10年为5天,10-20年为10天,20年以上为15天. 注意是累计工龄,不是本单位工龄. 如果该员工累计工龄满10年则有10天,否则为5天。",
                    reason="回答含糊且错误 — 没有区分累计工龄和本单位工龄,给出了错误的统一天数",
                    status="pending",
                    created_at=datetime.utcnow() - timedelta(hours=18),
                ),
                BadCase(
                    id=str(uuid.uuid4()),
                    question="合同印花税是多少?",
                    bad_answer="印花税税率为万分之五。",
                    expected_answer="不同合同类型税率不同:买卖合同万分之三,借款合同万分之零点五,技术合同万分_three,财产租赁合同千分之一。",
                    reason="笼统回答 — 只给了一个税率,实际上2022年新印花税法区分了多种合同类型",
                    status="pending",
                    created_at=datetime.utcnow() - timedelta(hours=6),
                ),
            ]
            session.add_all(bad_cases)
            t_logger.info(f"  🐛 Created {len(bad_cases)} bad cases")

        await session.commit()
    t_logger.success("🎉 Comprehensive evaluation data seeding completed!", action="seed_success")


if __name__ == "__main__":
    asyncio.run(seed_eval_data())
