"""
Application configuration — loaded from environment variables / .env file.
"""

from enum import Enum
from typing import Literal

from pydantic_settings import BaseSettings


class PlatformMode(str, Enum):
    """Platform deployment mode — controls which modules are activated."""
    RAG = "rag"           # Pure RAG platform (knowledge retrieval only)
    AGENT = "agent"       # Pure Agent platform (LLM orchestration only)
    FULL = "full"         # RAG + Agent combined (default)


class Settings(BaseSettings):
    """Global application settings."""

    # === App ===
    APP_NAME: str = "HiveMind RAG"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # === Platform Mode ===
    # Controls which modules are activated at startup.
    # "rag"   → Knowledge base, retrieval, ingestion, evaluation (no Agent Swarm)
    # "agent" → Agent Swarm, skills, MCP, tools (no RAG pipeline)
    # "full"  → All modules enabled (default)
    PLATFORM_MODE: PlatformMode = PlatformMode.FULL

    @property
    def rag_enabled(self) -> bool:
        """Whether RAG modules should be activated."""
        return self.PLATFORM_MODE in (PlatformMode.RAG, PlatformMode.FULL)

    @property
    def agent_enabled(self) -> bool:
        """Whether Agent modules should be activated."""
        return self.PLATFORM_MODE in (PlatformMode.AGENT, PlatformMode.FULL)

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
    DEFAULT_REASONING_MODEL: str = "kimi-k2.5"            # Specialized Reasoning
    DEFAULT_EMBEDDING_MODEL: str = "embedding-3"
    
    # === Generic LLM Configuration (Global Fallback) ===
    LLM_PROVIDER: str = "siliconflow"  # openai | deepseek | siliconflow | moonshot
    LLM_MODEL: str = "deepseek-ai/DeepSeek-V3"
    LLM_BASE_URL: str | None = None
    LLM_API_KEY: str | None = None

    # SiliconFlow Specific Models for Routing
    MODEL_GLM5: str = "Pro/zai-org/GLM-5"
    MODEL_DEEPSEEK_V3: str = "Pro/deepseek-ai/DeepSeek-V3"

    # === Tier Specific Providers (Optional overrides) ===
    REASONING_PROVIDER: str | None = "moonshot" 
    BALANCED_PROVIDER: str | None = "siliconflow"
    FAST_PROVIDER: str | None = "siliconflow"

    # === Knowledge Graph (Neo4j) ===
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # === Multimodal Model (Kimi/Moonshot) ===
    KIMI_API_KEY: str = ""
    KIMI_API_BASE: str = "https://api.moonshot.cn/v1" # Match .env name
    KIMI_MODEL: str = "moonshot-v1-8k"

    # === MCP ===
    MCP_SERVERS_CONFIG_PATH: str = "mcp_servers.json"

    # === Auth ===
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes (short-lived)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # === External Learning ===
    LEARNING_FETCH_INTERVAL_HOURS: int = 6
    GITHUB_TOKEN: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True, "extra": "ignore"}

    def __init__(self, **data):
        super().__init__(**data)
        # 强制从环境变量重新加载以确保覆盖
        if (
            self.POSTGRES_SERVER
            and self.POSTGRES_USER
            and self.POSTGRES_PASSWORD
            and self.POSTGRES_DB
        ):
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


settings = Settings()
