from pathlib import Path

from pydantic_settings import BaseSettings

# 计算后端根目录 (C:\Users\... \aiproject\backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Global application settings."""

    # === App ===
    APP_NAME: str = "HiveMind RAG"
    APP_VERSION: str = "0.1.0"
    BASE_DIR: Path = BASE_DIR
    DEBUG: bool = True
    ENV: str = "development"  # development | production | test

    # 基于 BASE_DIR 的绝对存储路径
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    CHECKPOINT_DB_PATH: Path = BASE_DIR / "storage" / "swarm_checkpoints.sqlite"

    # === Token Governance (P0 Hardening) ===
    # Standard 32K context window budget (Reference: REQ-014)
    CONTEXT_WINDOW_LIMIT: int = 32768
    # Percentage-based budgets (Total must be <= 1.0)
    BUDGET_SYSTEM_RATIO: float = 0.10
    BUDGET_MEMORY_RATIO: float = 0.15
    BUDGET_RAG_RATIO: float = 0.45
    BUDGET_HISTORY_RATIO: float = 0.20
    BUDGET_OUTPUT_RATIO: float = 0.10

    # === LLM Cost Budget (M7.1 Hardening) ===
    BUDGET_DAILY_LIMIT_USD: float = 10.0      # Daily cap in USD
    BUDGET_MONTHLY_LIMIT_USD: float = 100.0   # Monthly cap
    BUDGET_ALERT_THRESHOLD: float = 0.8       # Alert at 80% usage

    # === Sandbox Governance (P0 Hardening) ===
    SANDBOX_TIMEOUT_SEC: float = 5.0
    SANDBOX_MAX_RECURSION: int = 500

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

    # === Service Governance (Phase 5 / TASK-SG-001) ===
    # monolith: 单体模式（默认）
    # split:    读写分离模式（Retrieval/Ingestion 逻辑隔离）
    SERVICE_TOPOLOGY_MODE: str = "monolith"
    # 灰度开关：仅在 split 模式生效，按 user_id/query hash 百分比分流到 split 路径。
    SERVICE_GOVERNANCE_GRAY_PERCENT: int = 0
    # 预留：未来双服务部署时用于配置独立入口。
    RETRIEVAL_SERVICE_URL: str | None = None
    INGESTION_SERVICE_URL: str | None = None

    # === Dependency Circuit Breakers (Phase 5 / TASK-SG-003) ===
    CB_ENABLED: bool = True
    CB_WINDOW_SIZE: int = 20
    CB_MIN_REQUESTS: int = 10
    CB_ERROR_RATE_THRESHOLD: float = 0.5
    CB_OPEN_DURATION_SEC: int = 300
    CB_HALF_OPEN_PROBES: int = 2
    CB_TIMEOUT_LLM_MS: int = 30000
    CB_TIMEOUT_ES_MS: int = 8000
    CB_TIMEOUT_NEO4J_MS: int = 5000

    # === Vector Store ===
    VECTOR_STORE_TYPE: str = "elasticsearch"  # chroma | milvus | qdrant | elasticsearch

    # ChromaDB
    CHROMA_HOST: str | None = None   # None = 本地模式；设置后连接远程容器
    CHROMA_PORT: int = 8000

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
    DEFAULT_SIMPLE_MODEL: str = "deepseek-ai/DeepSeek-V3"    # Factual lookups, greetings
    DEFAULT_MEDIUM_MODEL: str = "deepseek-ai/DeepSeek-V3"    # Summaries, data extraction
    DEFAULT_COMPLEX_MODEL: str = "Pro/zai-org/GLM-5"         # Code generation, analysis
    DEFAULT_REASONING_MODEL: str = "deepseek-reasoner"       # Proofs, formal logic

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
    TAVILY_API_KEY: str = ""

    # === External Learning ===
    LEARNING_FETCH_INTERVAL_HOURS: int = 6
    GITHUB_TOKEN: str = ""
    MOCK_USER_HASH: str = "dev-password-placeholder"
    GITHUB_REPO_OWNER: str = "zxl85813-web"
    GITHUB_REPO_NAME: str = "HiveMind_RAG"
    GITHUB_PROJECT_OWNER: str = ""
    GITHUB_PROJECT_NUMBER: int = 0
    SELF_LEARNING_REPORT_DIR: Path = BASE_DIR / "docs" / "learning" / "daily"
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
