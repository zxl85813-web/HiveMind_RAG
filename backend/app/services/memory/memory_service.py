from datetime import datetime
from pathlib import Path

import chromadb
from loguru import logger

DATA_DIR = Path("data/memories")

# Initialize Local Vector Store
chroma_client = chromadb.PersistentClient(path="./start_data/chroma_db")
# Use a simple collection for memories
memory_collection = chroma_client.get_or_create_collection(name="agent_memories")


class MemoryService:
    """
    OpenClaw-style Memory System Implementation.
    Features:
    1. File-based persistent context (Markdown).
    2. Semantic Search via ChromaDB (Local).
    3. Daily Logging.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = DATA_DIR / user_id
        self.logs_dir = self.user_dir / "logs"
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure memory directory structure exists."""
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize core memory files if not exist
        for file in ["USER.md", "KNOWLEDGE.md"]:
            if not (self.user_dir / file).exists():
                file_path = self.user_dir / file
                file_path.write_text(f"# {file.split('.')[0]}\n\n", encoding="utf-8")

                # Index initial file content if needed
                # self.add_memory(file_path.read_text(), metadata={"source": file})

    def _get_daily_log_path(self, date_str: str = None) -> Path:
        """Get path for daily log file."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return self.logs_dir / f"{date_str}.md"

    async def _extract_and_index_abstract(self, doc_id: str, content: str, role: str):
        """Use LLM to generate an abstract and store it in Tier-1 Memory."""
        from app.core.llm import get_llm_service
        from app.services.memory.tier.abstract_index import abstract_index
        import json

        llm = get_llm_service()
        prompt = f"""
        Analyze the following memory segment and extract metadata in JSON format EXACTLY as below:
        {{
            "title": "Short title, max 5 words",
            "tags": ["tag1", "tag2"], // lowercase, technical or topical keywords
            "type": "{'user_query' if role == 'user' else 'ai_response'}" // Or 'log', 'concept', etc.
        }}
        Content:
        {content}
        """
        try:
            # We enforce JSON generation
            resp = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp)
            abstract_index.add_abstract(
                doc_id=doc_id,
                title=data.get("title", "Untitled Fragment"),
                doc_type=data.get("type", "log"),
                tags=data.get("tags", ["general"])
            )
            logger.info(f"⚡ Abstract Indexed | {data.get('title')} | Tags: {data.get('tags')}")
        except Exception as e:
            logger.warning(f"Failed to extract abstract for {doc_id}: {e}. Retrying with basic tags.")
            # Fallback
            abstract_index.add_abstract(doc_id, "Memory Fragment", role, ["fallback"])

    async def add_memory(self, content: str, metadata: dict = None):
        """
        Add a memory fragment to Vector Store and Tier-1 Index.
        """
        if not content.strip():
            return

        doc_id = f"{self.user_id}-{int(datetime.now().timestamp() * 1000)}"
        meta = metadata or {}
        role = meta.get("role", "system")
        meta.update({"user_id": self.user_id, "timestamp": datetime.now().isoformat()})

        import asyncio
        # Fire-and-forget: Build the abstract index asynchronously
        asyncio.create_task(self._extract_and_index_abstract(doc_id, content, role))

        # Add to Tier-2 (Neo4j Graph) asynchronously
        from app.services.memory.tier.graph_index import graph_index
        asyncio.create_task(graph_index.extract_and_store(doc_id, content))

        # Add to Vector Store (Tier-3)
        memory_collection.add(documents=[content], metadatas=[meta], ids=[doc_id])
        logger.info(f"Memory added to Vector Store: {doc_id}")

    async def log_interaction(self, role: str, content: str):
        """
        Append interaction to daily log (Ephemeral Memory) AND Index it.
        """
        # 1. Write to File (Reliability)
        log_file = self._get_daily_log_path()
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"\n### [{timestamp}] {role.upper()}\n{content}\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)

        # 2. Index to Vector Store (Retrieval)
        # We only index User messages or significant Agent conclusions to save noise
        if role == "user" or len(content) > 50:
            await self.add_memory(content, metadata={"source": "daily_log", "role": role})

    async def update_user_profile(self, content: str):
        """
        Update USER.md (Durable Memory).
        """
        file_path = self.user_dir / "USER.md"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n- {content}")

        # Also index this important fact
        await self.add_memory(content, metadata={"source": "user_profile", "type": "fact"})

    async def get_context(self, query: str = None) -> str:
        """
        Assemble context: Static Files + Daily Logs + Vector Search Results.
        """
        context = []

        # 1. User Profile (Always Top Priority)
        if (self.user_dir / "USER.md").exists():
            profile = (self.user_dir / "USER.md").read_text(encoding="utf-8")
            context.append(f"--- USER PROFILE ---\n{profile}")

        # 2. Vector Search (Relevant Past)
        if query:
            results = memory_collection.query(
                query_texts=[query],
                n_results=3,
                where={"user_id": self.user_id},  # Filter by user
            )
            if results["documents"]:
                retrieved = "\n".join([doc for doc in results["documents"][0]])
                context.append(f"--- RELEVANT MEMORY ---\n{retrieved}")

        # 3. Recent Logs (Immediate Context)
        daily_log = self._get_daily_log_path()
        if daily_log.exists():
            # Read last 2000 chars roughly
            logs = daily_log.read_text(encoding="utf-8")[-2000:]
            context.append(f"--- TODAY'S LOGS ---\n...{logs}")

        return "\n\n".join(context)

    async def search_memory(self, query: str, limit: int = 5) -> list[str]:
        """
        Expose search capability to Agents.
        """
        results = memory_collection.query(query_texts=[query], n_results=limit, where={"user_id": self.user_id})
        return results["documents"][0] if results["documents"] else []
