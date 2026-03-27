import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Set dummy env vars for spec generation
os.environ["EMBEDDING_API_KEY"] = "mock-key"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["ARK_API_KEY"] = "mock-key"
os.environ["SECRET_KEY"] = "mock-secret"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock Embedding Service to avoid API calls during import
import app.core.embeddings
mock_service = MagicMock()
mock_service.embed_query.return_value = [0.0] * 1536 # Standard embedding size
app.core.embeddings.get_embedding_service = lambda: mock_service

from app.main import app

def export_openapi():
    # Force openapi spec generation
    print("Gathering OpenAPI spec...")
    openapi_data = app.openapi()
    
    target_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "api"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_file = target_dir / "openapi.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(openapi_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ OpenAPI specification exported to: {target_file}")

if __name__ == "__main__":
    export_openapi()
