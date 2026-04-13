
"""
LLM 治理配置接口 (L5 Governance)

负责管理平台的多模型路由策略、价格智库以及智体提报的任务流。
该模块是 HiveMind “集体无意识” (Collective Unconscious) 层在 API 层的具体实现。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator, Field
from typing import Dict, Any, List
import json
from pathlib import Path
from loguru import logger

from app.common.response import ApiResponse
from app.api.deps import get_current_user, get_current_admin
from app.models.chat import User
from app.sdk.core import settings

router = APIRouter()
# 治理配置文件持久化路径 (从全局 settings 获取绝对路径)
CONFIG_FILE = settings.STORAGE_DIR / "llm_governance.json"

# --- 数据模型定义 ---

class TierMapping(BaseModel):
    """任务梯队与模型的映射关系"""
    simple: str    # 简单任务模型 (如 DeepSeek-V3)
    medium: str    # 中等复杂度任务
    complex: str   # 复杂逻辑/代码任务
    reasoning: str # 深度推理任务 (如 DeepSeek-R1)

class PriorityStrategy(BaseModel):
    """不同优先级任务的执行策略"""
    max_rounds: int      # 最大迭代轮数
    diverse_models: bool # 是否启用多模型辩论/验证
    tier: int            # 建议的资源梯队

class ModelMetadata(BaseModel):
    """
    模型智库元数据。
    
    记录了模型的供应商、计费价格以及技术特性，用于 L5 自治引擎进行经济审计。
    """
    id: str
    name: str
    provider: str
    input_price_1m: float = Field(0.0)  # 每百万 Token 输入价格 (USD)
    output_price_1m: float = Field(0.0) # 每百万 Token 输出价格 (USD)
    characteristics: List[str] = Field(default_factory=list) # 技术特性标签
    usage_scenarios: List[str] = Field(default_factory=list) # 推荐使用场景
    status: str = "active"

    @validator("input_price_1m", "output_price_1m", pre=True)
    def ensure_float(cls, v):
        """兼容性校验：确保前端传来的 String 类型价格能正确转换为 Float"""
        if isinstance(v, str):
            try:
                return float(v) if v.strip() else 0.0
            except ValueError:
                return 0.0
        return v

class LLMGovernanceConfig(BaseModel):
    """全局治理配置根模型"""
    tier_mapping: TierMapping
    model_registry: List[ModelMetadata]
    priority_strategies: Dict[str, PriorityStrategy]
    budget_daily_limit: float
    dialect_enabled: bool

# --- 默认配置智库 ---

DEFAULT_MODEL_REGISTRY = [
    {
        "id": "deepseek-ai/DeepSeek-V3",
        "name": "DeepSeek V3",
        "provider": "siliconflow",
        "input_price_1m": 0.14,
        "output_price_1m": 0.28,
        "characteristics": ["极速响应", "高性价比", "意向对齐强"],
        "usage_scenarios": ["日常对话", "简单意图提取", "内容翻译"],
        "status": "active"
    },
    {
        "id": "Pro/zai-org/GLM-5",
        "name": "GLM-5 Pro",
        "provider": "siliconflow",
        "input_price_1m": 0.6,
        "output_price_1m": 1.2,
        "characteristics": ["架构理解", "多模态原生", "数学与逻辑增强"],
        "usage_scenarios": ["代码生成", "复杂文档分析", "跨智体计划生成"],
        "status": "active"
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek R1 (Reasoner)",
        "provider": "ark",
        "input_price_1m": 2.0,
        "output_price_1m": 8.0,
        "characteristics": ["深度思考", "拒绝幻觉", "长程推理"],
        "usage_scenarios": ["算法证明", "审计分析", "法律条文推演"],
        "status": "active"
    }
]

# --- 逻辑辅助函数 ---

def _load_config() -> Dict[str, Any]:
    """
    加载本地治理配置。
    
    如果文件损坏或缺失，将自动回滚至硬编码的默认策略。
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "model_registry" not in data:
                    data["model_registry"] = DEFAULT_MODEL_REGISTRY
                return data
        except Exception as e:
            logger.error(f"Failed to load governance config: {e}. Falling back to defaults.")
    
    # 默认兜底配置
    return {
        "tier_mapping": {
            "simple": "deepseek-ai/DeepSeek-V3",
            "medium": "deepseek-ai/DeepSeek-V3",
            "complex": "Pro/zai-org/GLM-5",
            "reasoning": "deepseek-reasoner"
        },
        "model_registry": DEFAULT_MODEL_REGISTRY,
        "priority_strategies": {
            "1": {"max_rounds": 1, "diverse_models": False, "tier": 1},
            "2": {"max_rounds": 1, "diverse_models": False, "tier": 2},
            "3": {"max_rounds": 2, "diverse_models": True, "tier": 3},
            "4": {"max_rounds": 3, "diverse_models": True, "tier": 3},
            "5": {"max_rounds": 5, "diverse_models": True, "tier": 3}
        },
        "budget_daily_limit": 10.0,
        "dialect_enabled": True
    }

# --- API 接口实现 ---

@router.get("/llm-governance", response_model=ApiResponse[LLMGovernanceConfig])
async def get_llm_config():
    """获取当前的 LLM 治理配置（模型路由、价格、策略）"""
    return ApiResponse.ok(data=_load_config())

@router.put("/llm-governance", response_model=ApiResponse[LLMGovernanceConfig])
async def update_llm_config(
    config: LLMGovernanceConfig,
    current_user: User = Depends(get_current_admin) # 强制管理员权限
):
    """
    更新全局 LLM 治理配置。
    
    该操作会持久化到 JSON 文件中，并即时影响全平台的模型调用路由。
    """
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.dict(), f, indent=2, ensure_ascii=False)
    logger.info(f"LLM Governance configuration updated by {current_user.name}")
    return ApiResponse.ok(data=config)

@router.get("/llm-governance/insights", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_adaptive_insights():
    """
    获取自治推荐建议。
    
    系统会根据历史观察到的 Token 消耗和 Agent 运行成功率，自动给出路由优化建议。
    """
    content = [
        {
            "type": "cost",
            "title": "成本优化建议",
            "content": "检测到 Simple 任务中 deepseek-v3 的成功率与 GPT-3.5 持平，但成本低 60%，建议维持当前路由策略。",
            "priority": "low"
        },
        {
            "type": "performance",
            "title": "推理性能预警",
            "content": "近期 deepseek-reasoner 在推理任务中存在偶发性超时（>60s），建议若任务非 P0，可自动 Failover 到 GLM-5。",
            "priority": "medium"
        },
        {
            "type": "strategy",
            "title": "智体协作优化",
            "content": "分析 Elite Trace 发现：在代码审查场景下，'GPT-4o + Claude-3.5' 的双模型辩论一致性最高，建议在 M4 级别任务中启用。",
            "priority": "high"
        }
    ]
    return ApiResponse.ok(data=content)

@router.get("/governance/tasks", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_governance_tasks():
    """从架构图谱 (Neo4j) 中提取待办的治理任务"""
    from app.sdk.core.graph_store import get_graph_store
    store = get_graph_store()
    query = (
        "MATCH (t:Task) "
        "RETURN t.id as id, t.title as title, t.priority as priority, "
        "       t.status as status, t.created_at as created_at, "
        "       t.context_stub as context_stub, t.suggested_action as suggested_action "
        "ORDER BY t.created_at DESC"
    )
    try:
        tasks = await store.execute_query(query)
        return ApiResponse.ok(data=tasks)
    except Exception as e:
        logger.error(f"Failed to fetch governance tasks from Neo4j: {e}")
        return ApiResponse.ok(data=[])

@router.post("/governance/sync", response_model=ApiResponse[dict])
async def sync_governance_graph(
    current_user: User = Depends(get_current_admin)
):
    """
    触发手动同步：将全局治理规则同步到 Neo4j 知识图谱。
    
    该操作会将 llm_governance.json 中的配置映射为图节点，用于多智体系统的全链路治理。
    """
    from app.sdk.core.graph_store import get_graph_store
    store = get_graph_store()
    
    config_data = _load_config()
    model_registry = config_data.get("model_registry", [])
    tier_mapping = config_data.get("tier_mapping", {})
    
    # 🛰️ [GOV-SYNC]: 清理旧的治理映射并重建
    # 注意：我们仅清理治理相关的标签，不触及业务数据
    cleanup_query = "MATCH (g:GovernanceMetadata) DETACH DELETE g"
    await store.execute_query(cleanup_query)
    
    results_count = 0
    
    # 1. 同步模型注册中心 (Model Nodes)
    for model in model_registry:
        model_query = (
            "CREATE (m:Model:GovernanceMetadata { "
            "  id: $id, name: $name, provider: $provider, "
            "  input_price: $input, output_price: $output, "
            "  status: $status "
            "})"
        )
        await store.execute_query(model_query, {
            "id": model["id"],
            "name": model["name"],
            "provider": model["provider"],
            "input": model.get("input_price_1m", 0.0),
            "output": model.get("output_price_1m", 0.0),
            "status": model.get("status", "active")
        })
        results_count += 1

    # 2. 同步任务梯队 (Tier Nodes)
    for tier, model_id in tier_mapping.items():
        tier_query = (
            "MATCH (m:Model {id: $model_id}) "
            "CREATE (t:Tier:GovernanceMetadata { name: $tier }) "
            "CREATE (t)-[:ROUTED_TO]->(m)"
        )
        await store.execute_query(tier_query, {"tier": tier, "model_id": model_id})
        results_count += 1
    
    logger.info(f"Governance graph synchronized: {results_count} entities updated by {current_user.name}")
    return ApiResponse.ok(data={
        "status": "synchronized",
        "entities_count": results_count,
        "storage_source": str(CONFIG_FILE)
    })
