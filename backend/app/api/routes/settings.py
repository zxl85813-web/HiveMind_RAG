"""
Settings API — 平台内置知识库管理。

提供 CRUD 接口读写 platform_knowledge.yaml,
并在保存后自动 reload PromptEngine。
"""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from app.common.response import ApiResponse

router = APIRouter()

# === YAML 文件路径 ===
KNOWLEDGE_FILE = Path(__file__).parent.parent / "prompts" / "base" / "platform_knowledge.yaml"


# === Pydantic 模型 ===


class FeatureOperation(BaseModel):
    text: str


class PlatformFeature(BaseModel):
    name: str
    path: str
    description: str
    operations: list[str] = []


class FAQItem(BaseModel):
    q: str
    a: str


class PlatformKnowledge(BaseModel):
    overview: str = ""
    features: list[PlatformFeature] = []
    faq: list[FAQItem] = []


# === 工具函数 ===


def _read_yaml() -> dict:
    """读取 YAML 文件"""
    if not KNOWLEDGE_FILE.exists():
        return {}
    with open(KNOWLEDGE_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(data: dict) -> None:
    """写入 YAML 文件 (保留 meta)"""
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _reload_prompt_engine() -> None:
    """保存后自动重载 PromptEngine"""
    try:
        from app.prompts.engine import prompt_engine

        prompt_engine.reload()
        logger.info("PromptEngine reloaded after platform knowledge update")
    except Exception as e:
        logger.warning(f"Failed to reload PromptEngine: {e}")


# === API 端点 ===


@router.get("/platform-knowledge", response_model=ApiResponse[PlatformKnowledge])
async def get_platform_knowledge():
    """获取平台内置知识库内容"""
    data = _read_yaml()
    content = PlatformKnowledge(
        overview=data.get("overview", ""),
        features=[PlatformFeature(**f) for f in data.get("features", [])],
        faq=[FAQItem(**f) for f in data.get("faq", [])],
    )
    return ApiResponse.ok(data=content)


@router.put("/platform-knowledge", response_model=ApiResponse[PlatformKnowledge])
async def update_platform_knowledge(body: PlatformKnowledge):
    """更新平台内置知识库（整体覆盖 overview + features + faq）"""
    data = _read_yaml()

    # 保留 meta 字段
    meta = data.get("meta", {})

    new_data = {
        "meta": meta,
        "overview": body.overview,
        "features": [f.dict() for f in body.features],
        "faq": [f.dict() for f in body.faq],
    }

    _write_yaml(new_data)
    _reload_prompt_engine()

    return ApiResponse.ok(data=body)


@router.post("/platform-knowledge/features", response_model=ApiResponse[PlatformFeature])
async def add_feature(feature: PlatformFeature):
    """添加一个功能模块"""
    data = _read_yaml()
    features = data.get("features", [])
    features.append(feature.dict())
    data["features"] = features
    _write_yaml(data)
    _reload_prompt_engine()
    return ApiResponse.ok(data=feature)


@router.delete("/platform-knowledge/features/{feature_name}", response_model=ApiResponse)
async def delete_feature(feature_name: str):
    """删除一个功能模块"""
    data = _read_yaml()
    features = data.get("features", [])
    new_features = [f for f in features if f.get("name") != feature_name]
    if len(new_features) == len(features):
        raise HTTPException(status_code=404, detail=f"Feature '{feature_name}' not found")
    data["features"] = new_features
    _write_yaml(data)
    _reload_prompt_engine()
    return ApiResponse.ok(message=f"Feature '{feature_name}' deleted")


@router.post("/platform-knowledge/faq", response_model=ApiResponse[FAQItem])
async def add_faq(faq: FAQItem):
    """添加一条 FAQ"""
    data = _read_yaml()
    faqs = data.get("faq", [])
    faqs.append(faq.dict())
    data["faq"] = faqs
    _write_yaml(data)
    _reload_prompt_engine()
    return ApiResponse.ok(data=faq)


@router.delete("/platform-knowledge/faq/{index}", response_model=ApiResponse)
async def delete_faq(index: int):
    """删除一条 FAQ（按索引）"""
    data = _read_yaml()
    faqs = data.get("faq", [])
    if index < 0 or index >= len(faqs):
        raise HTTPException(status_code=404, detail=f"FAQ index {index} out of range")
    removed = faqs.pop(index)
    data["faq"] = faqs
    _write_yaml(data)
    _reload_prompt_engine()
    return ApiResponse.ok(message="FAQ deleted", data=removed)
