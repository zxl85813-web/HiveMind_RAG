
import os
import chromadb
from loguru import logger

def reset_eval_swarm():
    path = os.path.join(os.getcwd(), "data", "chroma")
    if not os.path.exists(path):
        logger.error(f"Chroma path not found: {path}")
        return

    client = chromadb.PersistentClient(path=path)
    collection_name = "eval_swarm"
    
    try:
        client.delete_collection(name=collection_name)
        logger.info(f"✅ Successfully deleted collection: {collection_name}")
    except Exception as e:
        logger.warning(f"⚠️ Could not delete collection {collection_name}: {e}")

if __name__ == "__main__":
    reset_eval_swarm()
