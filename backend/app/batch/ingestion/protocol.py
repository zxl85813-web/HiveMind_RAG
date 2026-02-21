"""
Data Protocol — Internal data structures for the Python Ingestion Pipeline.
"""

from enum import Enum
from typing import Any, List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# ============================================================
#  1. Metadata
# ============================================================

class ResourceType(str, Enum):
    """Types of resources supported by the ingestion system."""
    REQUIREMENT = "requirement"          # Word/Excel: 要件定義
    BASIC_DESIGN = "basic_design"        # Excel: 基本設計
    DETAIL_DESIGN = "detail_design"      # Excel: 詳細設計
    DB_SCHEMA = "db_schema"              # Excel/DDL
    SOURCE_CODE = "source_code"          # Java/Python code
    TEST_CASE = "test_case"              # Excel
    OTHER = "other"

class ResourceMetadata(BaseModel):
    """Metadata about the resource file."""
    filename: str
    file_path: str
    resource_type: ResourceType
    md5_checksum: str = ""
    
    # Versioning
    version: str = "1.0"
    last_modified_at: Optional[datetime] = None

# ============================================================
#  2. Content Structures
# ============================================================

class TableData(BaseModel):
    """Represents a structured table extracted from Excel/Word."""
    sheet_name: str = ""
    table_name: str = ""
    headers: List[str]
    rows: List[Dict[str, Any]]  # Keyed by header
    description: str = ""

class CodeSnippet(BaseModel):
    """Represents a block of code (Class, Method, SQL)."""
    language: str
    name: str                  # e.g. "UserDAO"
    signature: str             # e.g. "public class UserDAO"
    body: str
    start_line: int
    end_line: int
    related_comments: str = ""

class DocumentSection(BaseModel):
    """Represents a textual section."""
    title: str
    level: int
    content: str

class ImageContent(BaseModel):
    """Represents an image extracted from a document or standalone image file."""
    image_path: str = ""
    caption: str = ""
    ocr_text: str = ""
    page_number: int = 0
    confidence: float = 0.0

# ============================================================
#  3. The Payload
# ============================================================

class StandardizedResource(BaseModel):
    """
    The normalized format that all Parsers (Excel, MinerU, Code) must output.
    """
    meta: ResourceMetadata
    
    sections: List[DocumentSection] = []
    tables: List[TableData] = []
    codes: List[CodeSnippet] = []
    images: List[ImageContent] = []
    
    raw_text: str = ""
    
    # "Freestyle" annotations from AI (added later in pipeline)
    freestyle_tags: List[str] = []
    business_summary: str = ""
