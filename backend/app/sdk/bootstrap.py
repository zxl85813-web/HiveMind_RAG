import asyncio
from app.sdk.core import logger, settings
from app.sdk.harness.engine import get_harness_engine
from app.sdk.spec_engine import get_spec_engine
from app.sdk.discovery.scanner import discover_components
from app.sdk.discovery.registry import registry

async def bootstrap_system() -> None:
    """
    HiveMind 系统统一引导程序。
    负责初始化所有 SDK 核心组件、验证连接并加载安全护栏。
    """
    logger.info("============== HiveMind System Bootstrapping ==============")
    
    # 1. 验证基础配置
    logger.info(f"Environment: {settings.ENV} | Version: 0.1.0")
    
    # 2. 初始化 Spec 引擎并输出全景报告
    spec_engine = get_spec_engine()
    report = spec_engine.generate_report()
    logger.info(f"Spec Engine: [REQ: {report['by_category']['requirement']}] | "
                f"[DES: {report['by_category']['design']}] | "
                f"[Change: {report['by_category']['change']}]")
    logger.info(f"Spec Engine: Total {report['total']} specification entities registered.")
    
    # 3. 动态组件发现与图谱注册
    discover_components("app")
    await registry.sync_to_graph()
    
    # 4. 加载 AI 护栏 (Harness)
    harness = get_harness_engine()
    logger.info("Harness Engine: Active and monitoring for AI coding requests.")

    # 4. TODO: 后续集成 Neo4j 图谱同步与数据库 Seeding
    # from app.core.init_data import init_base_data
    # await init_base_data()

    logger.info("============== HiveMind Bootstrapping Complete =============")

if __name__ == "__main__":
    # 允许作为脚本独立运行进行环境自检
    asyncio.run(bootstrap_system())
