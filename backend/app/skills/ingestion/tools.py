"""
模块级 docstring — Ingestion Skill 工具集。

所属模块: skills.ingestion
依赖模块: app.batch.ingestion.protocol, app.batch.plugins
注册位置: REGISTRY.md > Skills > ingestion
"""
from typing import Any, Dict
from loguru import logger

# Import Core Ingestion components
from app.batch.ingestion.core import ParserRegistry, IngestionContext
from app.batch.ingestion.protocol import StandardizedResource

# Import plugins to ensure they are registered
# Import plugins through module paths to avoid circular imports?
# This depends on how plugin modules are structured.
import app.batch.plugins.mineru_parser
import app.batch.plugins.excel_parser

async def parse_file(file_path: str, filename: str = "") -> Dict[str, Any]:
    """
    Parse a file and return its structured content (StandardizedResource).
    
    Args:
        file_path: Absolute path to the file.
        filename: Original filename (used for extension detection).
    
    Returns:
        The content as a dictionary or an error dict.
    """
    logger.info(f"🧩 Skill[ingestion] parsing file: {file_path}")
    
    if not filename:
        # Fallback to filename from path
        import os
        filename = os.path.basename(file_path)
        
    parser = ParserRegistry.get_parser(filename)
    if not parser:
        logger.warning(f"⚠️ No parser found for {filename}")
        return {"error": f"No parser found for {filename}"}
        
    try:
        # Perform parsing
        resource: StandardizedResource = await parser.parse(file_path)
        
        # Convert Pydantic model to dict for serializability
        return resource.model_dump()
    except Exception as e:
        logger.error(f"❌ Parsing failed: {e}")
        return {"error": str(e)}

TOOLS = [parse_file]
