"""
Code Similarity Tool — AST-based structural similarity analysis.

Supports both TypeScript/TSX and Python files.
Outputs results to console, optional JSON file, and optional Neo4j graph.

Usage:
    python code_similarity_tool.py --dir frontend/src --threshold 0.7
    python code_similarity_tool.py --dir backend/app --lang python --threshold 0.7
    python code_similarity_tool.py --dir . --lang all --neo4j --threshold 0.65

Node/Relationship Schema (Neo4j):
    (:File)-[:SIMILAR_TO {score, block_a, block_b, detected_at}]->(:File)
    (:CodeEntity)-[:SIMILAR_TO {score, detected_at}]->(:CodeEntity)
"""

import os
import sys
import ast
import argparse
import glob
import re
import json
import hashlib
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter
from datetime import datetime
from loguru import logger

# Discovery BASE_DIR
BASE_DIR = Path(__file__).resolve().parents[3]
if not (BASE_DIR / "backend").exists():
    BASE_DIR = Path(os.getcwd())

# ─── Tree-sitter for TypeScript ───────────────────────────────────────────────

_tsx_parser = None
_tsx_block_query = None

def _init_tsx():
    global _tsx_parser, _tsx_block_query
    if _tsx_parser is not None:
        return True
    try:
        import tree_sitter_typescript as ts_typescript
        from tree_sitter import Language, Parser, Query
        TSX_LANGUAGE = Language(ts_typescript.language_tsx())
        _tsx_parser = Parser(TSX_LANGUAGE)
        _tsx_block_query = Query(TSX_LANGUAGE, """
            (function_declaration name: (identifier) @name) @block
            (variable_declarator 
                name: (identifier) @name 
                value: [(arrow_function) (function_expression)]) @block
            (method_definition name: (property_identifier) @name) @block
        """)
        return True
    except Exception as e:
        logger.warning(f"Tree-sitter TSX init failed (TS scanning disabled): {e}")
        return False


# ─── Fingerprinting ──────────────────────────────────────────────────────────

def get_ts_structural_fingerprint(node):
    """Generate AST type sequence fingerprint for a tree-sitter node."""
    fingerprint = []
    IGNORE_TYPES = {'comment', 'import_statement', 'export_statement', 'empty_statement'}
    def traverse(n):
        if n.type in IGNORE_TYPES:
            return
        fingerprint.append(n.type)
        for child in n.children:
            traverse(child)
    traverse(node)
    return " ".join(fingerprint)


def get_py_structural_fingerprint(node):
    """Generate AST type sequence fingerprint for a Python AST node."""
    fingerprint = []
    IGNORE_TYPES = {ast.Import, ast.ImportFrom}
    for child in ast.walk(node):
        if type(child) in IGNORE_TYPES:
            continue
        fingerprint.append(type(child).__name__)
    return " ".join(fingerprint)


# ─── Similarity Calculation ──────────────────────────────────────────────────

def calculate_similarity(fp1: str, fp2: str) -> float:
    """Two-phase similarity: fast Jaccard pre-filter, then SequenceMatcher."""
    c1 = Counter(fp1.split())
    c2 = Counter(fp2.split())
    intersection = sum((c1 & c2).values())
    union = sum((c1 | c2).values())
    if union == 0:
        return 0.0
    jaccard = intersection / union
    if jaccard < 0.4:
        return jaccard
    return SequenceMatcher(None, fp1, fp2).ratio()


# ─── TypeScript Scanner ──────────────────────────────────────────────────────

def scan_ts_blocks(search_dir: str, min_len: int = 10) -> list[dict]:
    """Extract function/method blocks from TypeScript/TSX files."""
    if not _init_tsx():
        return []

    base_path = Path(search_dir)
    files = []
    for ext in ['*.ts', '*.tsx']:
        files.extend(glob.glob(str(base_path / "**" / ext), recursive=True))

    records = []
    for f_path in files:
        if any(exc in f_path for exc in ['node_modules', '.git', 'dist', 'build']):
            continue
        try:
            with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if not content.strip():
                continue

            tree = _tsx_parser.parse(bytes(content, 'utf8'))
            rel_path = os.path.relpath(f_path, BASE_DIR).replace("\\", "/")

            captures = _tsx_block_query.captures(tree.root_node)
            block_data = {}
            for node, tag in captures:
                if tag == "block":
                    if node.id not in block_data:
                        block_data[node.id] = {"node": node, "name": "anonymous"}
                elif tag == "name":
                    p = node.parent
                    while p:
                        if p.id in block_data:
                            block_data[p.id]["name"] = node.text.decode("utf8")
                            break
                        p = p.parent

            for data in block_data.values():
                fp = get_ts_structural_fingerprint(data["node"])
                fp_len = len(fp.split())
                if fp_len >= min_len:
                    records.append({
                        "path": rel_path,
                        "name": data["name"],
                        "fingerprint": fp,
                        "length": fp_len,
                        "lang": "typescript",
                    })
        except Exception:
            pass

    return records


# ─── Python Scanner ──────────────────────────────────────────────────────────

def scan_py_blocks(search_dir: str, min_len: int = 10) -> list[dict]:
    """Extract function/class blocks from Python files."""
    base_path = Path(search_dir)
    py_files = glob.glob(str(base_path / "**" / "*.py"), recursive=True)

    records = []
    for f_path in py_files:
        if any(exc in f_path for exc in ['.agent', '.venv', 'node_modules', '.git', '__pycache__']):
            continue
        try:
            with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if not content.strip():
                continue

            tree = ast.parse(content)
            rel_path = os.path.relpath(f_path, BASE_DIR).replace("\\", "/")

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fp = get_py_structural_fingerprint(node)
                    fp_len = len(fp.split())
                    if fp_len >= min_len:
                        # Determine qualified name
                        name = node.name
                        records.append({
                            "path": rel_path,
                            "name": name,
                            "fingerprint": fp,
                            "length": fp_len,
                            "lang": "python",
                        })
                elif isinstance(node, ast.ClassDef):
                    # Index class-level methods
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            fp = get_py_structural_fingerprint(item)
                            fp_len = len(fp.split())
                            if fp_len >= min_len:
                                records.append({
                                    "path": rel_path,
                                    "name": f"{node.name}.{item.name}",
                                    "fingerprint": fp,
                                    "length": fp_len,
                                    "lang": "python",
                                })
        except Exception:
            pass

    return records


# ─── Cross-language Comparison ───────────────────────────────────────────────

def find_similar_pairs(records: list[dict], threshold: float = 0.7) -> list[dict]:
    """Compare all block pairs and return those above threshold."""
    results = []
    num = len(records)
    logger.info(f"Comparing {num} blocks (threshold={threshold})...")

    for i in range(num):
        for j in range(i + 1, num):
            r1, r2 = records[i], records[j]
            # Skip same block
            if r1['path'] == r2['path'] and r1['name'] == r2['name']:
                continue
            # Skip wildly different sizes
            ratio = r1['length'] / r2['length'] if r2['length'] else 999
            if ratio > 2.5 or ratio < 0.4:
                continue
            # Only compare same language (AST types differ across languages)
            if r1['lang'] != r2['lang']:
                continue

            sim = calculate_similarity(r1['fingerprint'], r2['fingerprint'])
            if sim >= threshold:
                results.append({
                    "block1_path": r1['path'],
                    "block1_name": r1['name'],
                    "block2_path": r2['path'],
                    "block2_name": r2['name'],
                    "similarity": round(sim, 4),
                    "lang": r1['lang'],
                })

    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results


# ─── Neo4j Writer ────────────────────────────────────────────────────────────

def write_similarity_to_neo4j(results: list[dict], neo4j_driver):
    """
    Write SIMILAR_TO relationships into Neo4j.

    Creates two levels of relationships:
    1. File-level:  (:File)-[:SIMILAR_TO]->(:File)  with max score between any blocks
    2. Block-level: (:CodeEntity)-[:SIMILAR_TO]->(:CodeEntity)  per block pair
    """
    if not neo4j_driver:
        logger.warning("No Neo4j driver — skipping graph write.")
        return

    now = datetime.now().isoformat()

    # 1. Clear stale SIMILAR_TO relationships (full refresh)
    with neo4j_driver.session() as session:
        session.run("MATCH ()-[r:SIMILAR_TO]->() DELETE r")
        logger.info("🧹 Cleared old SIMILAR_TO relationships.")

    # 2. Aggregate file-level max similarity
    file_pairs: dict[tuple, dict] = {}
    for r in results:
        key = tuple(sorted([r['block1_path'], r['block2_path']]))
        if key not in file_pairs or r['similarity'] > file_pairs[key]['similarity']:
            file_pairs[key] = r

    # 3. Write file-level SIMILAR_TO
    with neo4j_driver.session() as session:
        for (path_a, path_b), data in file_pairs.items():
            if path_a == path_b:
                continue
            session.run("""
                MATCH (a:File {id: $path_a})
                MATCH (b:File {id: $path_b})
                MERGE (a)-[r:SIMILAR_TO]->(b)
                SET r.score = $score,
                    r.block_a = $block_a,
                    r.block_b = $block_b,
                    r.lang = $lang,
                    r.detected_at = $detected_at
            """, {
                "path_a": path_a,
                "path_b": path_b,
                "score": data['similarity'],
                "block_a": f"{data['block1_path']}::{data['block1_name']}",
                "block_b": f"{data['block2_path']}::{data['block2_name']}",
                "lang": data['lang'],
                "detected_at": now,
            })

    logger.info(f"📊 Wrote {len(file_pairs)} file-level SIMILAR_TO relationships.")

    # 4. Write block-level SIMILAR_TO (CodeEntity nodes)
    block_count = 0
    with neo4j_driver.session() as session:
        for r in results:
            entity_a = f"{r['block1_path']}::{r['block1_name']}"
            entity_b = f"{r['block2_path']}::{r['block2_name']}"
            res = session.run("""
                MATCH (a:CodeEntity {id: $id_a})
                MATCH (b:CodeEntity {id: $id_b})
                MERGE (a)-[r:SIMILAR_TO]->(b)
                SET r.score = $score, r.detected_at = $detected_at
                RETURN count(r) AS cnt
            """, {
                "id_a": entity_a,
                "id_b": entity_b,
                "score": r['similarity'],
                "detected_at": now,
            })
            cnt = res.single()
            if cnt and cnt["cnt"] > 0:
                block_count += 1

    logger.info(f"🔗 Wrote {block_count} block-level SIMILAR_TO relationships.")


# ─── Main ────────────────────────────────────────────────────────────────────

def scan_codebase_similarity(
    search_dir: str,
    threshold: float = 0.7,
    min_len: int = 10,
    lang: str = "all",
    output_json: str | None = None,
    neo4j_driver=None,
) -> list[dict]:
    """
    Full pipeline: scan → compare → report → (optional) write to Neo4j.
    """
    records = []

    if lang in ("all", "typescript"):
        ts_records = scan_ts_blocks(search_dir, min_len)
        logger.info(f"TypeScript: extracted {len(ts_records)} blocks.")
        records.extend(ts_records)

    if lang in ("all", "python"):
        py_records = scan_py_blocks(search_dir, min_len)
        logger.info(f"Python: extracted {len(py_records)} blocks.")
        records.extend(py_records)

    if not records:
        logger.warning("No code blocks found to compare.")
        return []

    results = find_similar_pairs(records, threshold)

    # Console output
    print("\n" + "=" * 80)
    print(f"🚀 Block-level Similarity Results (TOP 15 / Total: {len(results)})")
    print("=" * 80)
    for idx, res in enumerate(results[:15]):
        print(
            f"RANK {idx+1}: {res['similarity']*100:.1f}% [{res['lang']}]\n"
            f"  A: {res['block1_path']}::{res['block1_name']}\n"
            f"  B: {res['block2_path']}::{res['block2_name']}"
        )

    # JSON output
    if output_json:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"📄 Results saved to {output_json}")

    # Neo4j output
    if neo4j_driver:
        write_similarity_to_neo4j(results, neo4j_driver)

    return results


if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(description="AST-based Code Similarity Tool (TS + Python)")
    parser_cli.add_argument("--dir", default=".", help="Root directory to scan")
    parser_cli.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0.0 - 1.0)")
    parser_cli.add_argument("--min-len", type=int, default=10, help="Minimum AST node count per block")
    parser_cli.add_argument("--lang", choices=["all", "typescript", "python"], default="all", help="Language filter")
    parser_cli.add_argument("--json", help="Path to save JSON report")
    parser_cli.add_argument("--neo4j", action="store_true", help="Write results to Neo4j")
    args = parser_cli.parse_args()

    driver = None
    if args.neo4j:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / "backend" / ".env")
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "neo4j123")
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")

    scan_codebase_similarity(
        search_dir=args.dir,
        threshold=args.threshold,
        min_len=args.min_len,
        lang=args.lang,
        output_json=args.json,
        neo4j_driver=driver,
    )

    if driver:
        driver.close()
