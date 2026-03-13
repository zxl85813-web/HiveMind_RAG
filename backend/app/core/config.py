"""
Application configuration — loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings."""

    # === App ===
    APP_NAME: str = "HiveMind RAG"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # === CORS ===
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # === PostgreSQL ===
    POSTGRES_SERVER: str | None = "localhost"
    POSTGRES_USER: str | None = "postgres"
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = "hivemind"
    POSTGRES_PORT: int = 5432

    # === Database (Auto-generated from PostgreSQL or default to SQLite) ===
    DATABASE_URL: str = "sqlite+aiosqlite:///./hivemind.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # === Vector Store ===
    VECTOR_STORE_TYPE: str = "elasticsearch"  # chroma | milvus | qdrant | elasticsearch

    # Elasticsearch (Matches .env keys)
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_API_KEY: str | None = None
    ES_INDEX_PREFIX: str = "hivemind"

    # === Embedding ===
    EMBEDDING_PROVIDER: str = "zhipu"
    EMBEDDING_MODEL: str = "embedding-3"
    EMBEDDING_API_KEY: str | None = None
    EMBEDDING_DIMS: int = 2048

    # === LLM Providers ===
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # Default LLM for different tasks (HVM - HiveMind Architecture)
    DEFAULT_CHAT_MODEL: str = "deepseek-ai/DeepSeek-V3.2"  # Flagship Balanced
    DEFAULT_REASONING_MODEL: str = "kimi-k2.5"  # Specialized Reasoning
    DEFAULT_EMBEDDING_MODEL: str = "embedding-3"

    # === Generic LLM Configuration (Global Fallback) ===
    LLM_PROVIDER: str = "siliconflow"  # openai | deepseek | siliconflow | moonshot
    LLM_MODEL: str = "deepseek-ai/DeepSeek-V3"
    LLM_BASE_URL: str | None = None
    LLM_API_KEY: str | None = None

    # SiliconFlow Specific Models for Routing
    MODEL_GLM5: str = "Pro/zai-org/GLM-5"
    MODEL_DEEPSEEK_V3: str = "Pro/deepseek-ai/DeepSeek-V3"

    # === ClawRouter 4-Tier Models (Cost Optimization) ===
    DEFAULT_SIMPLE_MODEL: str = "deepseek-ai/DeepSeek-V3"  # Factual lookups, greetings, translations (e.g. Gemini Flash)
    DEFAULT_MEDIUM_MODEL: str = "deepseek-ai/DeepSeek-V3"  # Summaries, explanations, data extraction (e.g. DeepSeek Chat)
    DEFAULT_COMPLEX_MODEL: str = "Pro/zai-org/GLM-5"       # Code generation, multi-step analysis (e.g. Claude Opus)
    DEFAULT_REASONING_MODEL: str = "deepseek-reasoner"     # Proofs, formal logic, multi-step math (e.g. o3 / o1)

    # === Tier Specific Providers (Optional overrides) ===
    SIMPLE_PROVIDER: str | None = "siliconflow"
    MEDIUM_PROVIDER: str | None = "siliconflow"
    COMPLEX_PROVIDER: str | None = "siliconflow"
    REASONING_PROVIDER: str | None = "ark"

    # === Knowledge Graph (Neo4j) ===
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""  # Should be set via .env

    # === Multimodal Model (Kimi/Moonshot) ===
    KIMI_API_KEY: str = ""
    KIMI_API_BASE: str = "https://api.moonshot.cn/v1"  # Match .env name
    KIMI_MODEL: str = "moonshot-v1-8k"

    # === MCP ===
    MCP_SERVERS_CONFIG_PATH: str = "mcp_servers.json"

    # === Auth ===
    SECRET_KEY: str = ""  # CRITICAL: Must be set in .env for production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes (short-lived)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # === External Learning ===
    LEARNING_FETCH_INTERVAL_HOURS: int = 6
    GITHUB_TOKEN: str = ""
    MOCK_USER_HASH: str = "dev-password-placeholder"
    GITHUB_REPO_OWNER: str = "zxl85813-web"
    GITHUB_REPO_NAME: str = "HiveMind_RAG"
    GITHUB_PROJECT_OWNER: str = ""
    GITHUB_PROJECT_NUMBER: int = 0
    SELF_LEARNING_REPORT_DIR: str = "docs/learning/daily"
    SELF_LEARNING_ISSUE_LIMIT: int = 20
    SELF_LEARNING_X_ACCOUNTS: str = "OpenAI,AnthropicAI,GoogleDeepMind,MetaAI,xai,QwenLM"
    SELF_LEARNING_AI_FEEDS: str = (
        "https://openai.com/news/rss.xml,"
        "https://www.anthropic.com/news/rss.xml,"
        "https://deepmind.google/discover/blog/rss.xml"
    )
    SELF_LEARNING_GITHUB_WATCH_REPOS: str = (
        "openai/openai-python,anthropics/anthropic-sdk-python,google-gemini/generative-ai-python,"
        "huggingface/transformers,langchain-ai/langchain,microsoft/autogen"
    )

    # === Crawler — GitHub Trending ===
    LEARNING_GITHUB_TRENDING_LANGUAGE: str = "python"
    LEARNING_GITHUB_TRENDING_LIMIT: int = 5

    # === Crawler — Hacker News ===
    LEARNING_HN_MIN_SCORE: int = 100
    LEARNING_HN_LIMIT: int = 5

    # === Crawler — ArXiv ===
    # Comma-separated ArXiv category IDs (cs.AI, cs.CL, cs.IR, cs.LG, …)
    LEARNING_ARXIV_CATEGORIES: str = "cs.AI,cs.CL,cs.IR"
    LEARNING_ARXIV_MAX_RESULTS: int = 5

    # === Relevance Model ===
    # Comma-separated tech stack terms used as context in LLM relevance scoring.
    LEARNING_TECH_STACK_CONTEXT: str = (
        "FastAPI,LangChain,LangGraph,RAG,Vector Database,Knowledge Graph,"
        "Python,TypeScript,React,PostgreSQL,Redis,Docker,Agent Swarm,Embedding"
    )
    # Discoveries below this threshold are discarded before storing.
    LEARNING_RELEVANCE_MIN_SCORE: float = 0.45

    # === ARK Deep Interpretation ===
    ARK_API_KEY: str = ""
    ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    ARK_MODEL: str = "deepseek-v3-2-251201"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True, "extra": "ignore"}

    def __init__(self, **data):
        super().__init__(**data)
        import os

        testing = os.environ.get("TESTING") == "1"

        # 强制从环境变量重新加载以确保覆盖 (如果不是在测试模式)
        if not testing and self.POSTGRES_SERVER and self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
            from urllib.parse import quote_plus

            # URL-encode 密码，防止 @ 等特殊字符破坏 URL 解析
            encoded_password = quote_plus(str(self.POSTGRES_PASSWORD))
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
            import sys

            # logger 可能还未完全初始化，使用 stderr 打印关键配置路径
            print(f"[DB] Database mapped to PostgreSQL: {self.POSTGRES_SERVER}", file=sys.stderr)
        elif testing:
            import sys

            print("[DB] Running in TESTING mode - Database URL preserved", file=sys.stderr)


settings = Settings()
