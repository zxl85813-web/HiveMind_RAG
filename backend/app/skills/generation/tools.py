from typing import List, Optional, Dict, Any
from app.services.generation import get_generation_service
from app.services.memory.tier.abstract_index import abstract_index

async def generate_design_document(task_description: str, kb_ids: List[str]) -> str:
    """
    Generates a structured design document (e.g., Test Plan, API Spec) based on the provided task description and Knowledge Base IDs.
    
    The process involves:
    1. Retrieving relevant context from the specified KBs.
    2. Drafting an initial version of the document.
    3. Self-correcting and refining the draft.
    4. Exporting the final result to a CSV file (Excel compatible).
    
    Args:
        task_description: A detailed description of what to generate (e.g., "Create a test plan for the Login module including negative cases").
        kb_ids: A list of Knowledge Base IDs to use as context.
        
    Returns:
        A message indicating success and the path to the generated file.
    """
    service = get_generation_service()
    try:
        # Pipeline execution
        ctx = await service.run(task_description, kb_ids)
        
        if ctx.final_artifact_path:
            return f"✅ Document generated successfully!\nPath: {ctx.final_artifact_path}\n(You can download it or view it in Excel)"
        else:
            return "❌ Failed to generate document. Please check logs."
    except Exception as e:
        return f"❌ Error during generation: {str(e)}"

def search_abstract_memory(tags: List[str] = None, doc_types: List[str] = None, dates: List[str] = None) -> List[Dict[str, Any]]:
    """
    [Radar Tool] Instantly searches the In-Memory Tier-1 Abstract Index.
    Use this tool FIRST when trying to recall past conversations, logs, or knowledge before doing a deep vector search.
    
    Args:
        tags: List of keywords/tags to filter by (e.g., ["postgresql", "bug"]).
        doc_types: List of document types (e.g., ["user_query", "ai_response", "log"]).
        dates: List of specific dates in YYYY-MM-DD format.
        
    Returns:
        A list of highly relevant, lightweight abstract summaries (doc_id, title, tags, date).
        You can then use these IDs to fetch details if needed.
    """
    results = abstract_index.route_query(tags=tags, doc_types=doc_types, dates=dates)
    return results

def get_tools():
    return [generate_design_document, search_abstract_memory]
