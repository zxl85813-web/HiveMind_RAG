"""
SQLite Database MCP Server (P2 Implementation).
Uses FastMCP to provide structured data access to the Agent Swarm.
"""

from fastmcp import FastMCP
import sqlite3
import os
from typing import List, Dict, Any

# Initialize FastMCP server
mcp = FastMCP("DatabaseServer")

# Configuration (Path to the swarm checkpoints or a dedicated research DB)
DB_PATH = os.environ.get("MCP_DB_PATH", "storage/research_data.sqlite")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def list_tables() -> List[str]:
    """List all available tables in the research database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row["name"] for row in cursor.fetchall()]

@mcp.tool()
def describe_table(table_name: str) -> List[Dict[str, Any]]:
    """Get the schema (columns, types) for a specific table."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [dict(row) for row in cursor.fetchall()]

@mcp.tool()
def query_database(sql: str) -> str:
    """
    Execute a read-only SQL query on the research database.
    Use this to find structured evidence or perform data analysis.
    """
    if not sql.lower().strip().startswith("select"):
        return "Error: Only SELECT queries are allowed for security reasons."
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            if not rows:
                return "No results found."
            
            # Simple Markdown table output
            header = rows[0].keys()
            output = "| " + " | ".join(header) + " |\n"
            output += "| " + " | ".join(["---"] * len(header)) + " |\n"
            for row in rows[:20]: # Limit output to 20 rows
                output += "| " + " | ".join(str(row[k]) for k in header) + " |\n"
            
            if len(rows) > 20:
                output += f"\n... (Truncated {len(rows)-20} rows)"
            
            return output
    except Exception as e:
        return f"Database Error: {e!s}"

if __name__ == "__main__":
    # Ensure storage dir exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # Initialize a mock table for P2 demonstration if not exists
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, status TEXT, budget INTEGER);")
        conn.execute("DELETE FROM projects;") # Clear for demo
        conn.execute("INSERT INTO projects (name, status, budget) VALUES ('HiveMind Hardening', 'Active', 50000);")
        conn.execute("INSERT INTO projects (name, status, budget) VALUES ('Semantic RAG', 'M7.4', 35000);")
        conn.commit()
    
    mcp.run()
