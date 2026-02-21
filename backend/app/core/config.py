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

    # === Database ===
    DATABASE_URL: str = "sqlite+aiosqlite:///./hivemind.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # === Vector Store ===
    VECTOR_STORE_TYPE: str = "elasticsearch"  # chroma | milvus | qdrant | elasticsearch
    
    # Elasticsearch
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

    # Default LLM for different tasks
    DEFAULT_CHAT_MODEL: str = "gpt-4o-mini"
    DEFAULT_REASONING_MODEL: str = "deepseek-r1"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # === Generic LLM Configuration (e.g. SiliconFlow) ===
    LLM_PROVIDER: str = "openai"  # openai | deepseek | siliconflow | ollama
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str | None = None
    LLM_API_KEY: str | None = None

    # === MCP ===
    MCP_SERVERS_CONFIG_PATH: str = "mcp_servers.json"

    # === Auth ===
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # === External Learning ===
    LEARNING_FETCH_INTERVAL_HOURS: int = 6
    GITHUB_TOKEN: str = ""

    # === Knowledge Graph (Neo4j) ===
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # === Multimodal Model (Kimi/Moonshot) ===
    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k" # k2.5 alias if supported

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
