import asyncio
import sys
import os
from pathlib import Path

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("baseline_llm")
t_logger = get_trace_logger("scripts.baseline_llm")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

# Load .env
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from app.core.config import settings


async def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Calculate the fibonacci sequence up to 10"

    t_logger.info("🚀 Starting Baseline LLM Test...", action="baseline_start", meta={
        "prompt": prompt,
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL
    })

    # Initialize LLM directly (No Swarm, No Graph, No Supervisor)
    llm_kwargs = {
        "model": settings.LLM_MODEL,
        "temperature": 0,
    }

    if settings.LLM_PROVIDER == "siliconflow":
        llm_kwargs["base_url"] = settings.LLM_BASE_URL
        llm_kwargs["api_key"] = settings.LLM_API_KEY
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        llm_kwargs["api_key"] = settings.OPENAI_API_KEY

    llm = ChatOpenAI(**llm_kwargs)

    try:
        # Direct call
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        t_logger.success("Baseline Execution Completed", action="baseline_success")
        print("\n--- LLM Output ---\n")
        print(response.content)
        print("\n------------------\n")

    except Exception as e:
        t_logger.error(f"Baseline Execution Failed: {e}", action="baseline_failure")


if __name__ == "__main__":
    asyncio.run(main())
