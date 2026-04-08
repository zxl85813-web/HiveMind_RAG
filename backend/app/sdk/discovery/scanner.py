import os
import importlib
import pkgutil
from app.sdk.core import logger
from app.sdk.discovery.registry import registry

def discover_components(package_name: str = "app"):
    """
    递归扫描并导入指定包下的所有模块，触发 @register_component 装饰器。
    """
    logger.info(f"Discovery: Starting auto-scan for package: {package_name}")
    
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.error(f"Discovery: Failed to import base package {package_name}: {e}")
        return

    # 递归遍历包路径
    prefix = package.__name__ + "."
    for loader, modname, ispkg in pkgutil.walk_packages(package.__path__, prefix):
        try:
            # 排除自身扫描脚本和测试脚本
            if "test" in modname or "discovery.scanner" in modname:
                continue
                
            importlib.import_module(modname)
            logger.debug(f"Discovery: Imported module {modname}")
        except Exception as e:
            # 某些模块可能因为依赖问题无法导入，这里我们优雅跳过
            logger.warning(f"Discovery: Could not import {modname}: {e}")

    logger.info(f"Discovery: Scan complete. {len(registry.components)} components found in memory.")
