import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

# Load .env
from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from app.core.config import settings


async def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Calculate the fibonacci sequence up to 10"

    logger.info("🚀 Starting Baseline LLM Test...")
    logger.info(f"Config: Provider={settings.LLM_PROVIDER}, Model={settings.LLM_MODEL}")
    logger.info(f"Prompt: '{prompt}'")

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
        logger.success("Baseline Execution Completed.")
        print("\n--- LLM Output ---\n")
        print(response.content)
        print("\n------------------\n")

    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
