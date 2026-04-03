import os
import sys
import argparse
import glob
import re
from pathlib import Path
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Query
from difflib import SequenceMatcher
from collections import Counter
from loguru import logger
import json

# Discovery BASE_DIR
BASE_DIR = Path(__file__).resolve().parents[4]
if not (BASE_DIR / "backend").exists():
    BASE_DIR = Path(os.getcwd())

# 1. Initialize Tree-sitter for TSX
try:
    TSX_LANGUAGE = Language(ts_typescript.language_tsx())
    parser = Parser(TSX_LANGUAGE)
except Exception as e:
    logger.error(f"Failed to initialize Tree-sitter: {e}")
    sys.exit(1)

# Combined query for functions, arrow functions, and methods
BLOCK_QUERY = Query(TSX_LANGUAGE, """
(function_declaration name: (identifier) @name) @block
(variable_declarator 
    name: (identifier) @name 
    value: [(arrow_function) (function_expression)]) @block
(method_definition name: (property_identifier) @name) @block
""")

def get_structural_fingerprint(node):
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

def calculate_similarity(fp1, fp2):
    # Jaccard distance for fast pre-filter
    c1 = Counter(fp1.split())
    c2 = Counter(fp2.split())
    intersection = sum((c1 & c2).values())
    union = sum((c1 | c2).values())
    if union == 0: return 0.0
    jaccard = intersection / union
    
    if jaccard < 0.4: return jaccard
    return SequenceMatcher(None, fp1, fp2).ratio()

def scan_codebase_similarity(search_dir, threshold, min_len, output_json=None):
    base_path = Path(search_dir)
    files = []
    for ext in ['*.ts', '*.tsx']:
        files.extend(glob.glob(str(base_path / "**" / ext), recursive=True))
    
    logger.info(f"Scanning {len(files)} files into blocks (Threshold: {threshold})...")
    
    records = []
    for f_path in files:
        if any(exc in f_path for exc in ['node_modules', '.git', 'dist', 'build']):
            continue
        try:
            with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if not content.strip(): continue
                tree = parser.parse(bytes(content, 'utf8'))
                rel_path = os.path.relpath(f_path, base_path)
                
                # Slicing into blocks
                captures = BLOCK_QUERY.captures(tree.root_node)
                
                block_data = {}
                for node, tag in captures:
                    if tag == "block":
                        if node.id not in block_data:
                            block_data[node.id] = {"node": node, "name": "anonymous"}
                    elif tag == "name":
                        # Traverse up to find the block node
                        p = node.parent
                        while p:
                            if p.id in block_data:
                                block_data[p.id]["name"] = node.text.decode("utf8")
                                break
                            p = p.parent
                
                count = 0
                for data in block_data.values():
                    fp = get_structural_fingerprint(data["node"])
                    fp_len = len(fp.split())
                    if fp_len >= min_len:
                        records.append({
                            "path": rel_path,
                            "name": data["name"],
                            "fingerprint": fp,
                            "length": fp_len
                        })
                        count += 1
                        
        except Exception as e:
            # Optionally log e for debugging
            pass

    results = []
    num_records = len(records)
    logger.info(f"Comparing {num_records} blocks...")
    
    for i in range(num_records):
        for j in range(i + 1, num_records):
            r1, r2 = records[i], records[j]
            if r1['path'] == r2['path'] and r1['name'] == r2['name']:
                continue
            if r1['length'] / r2['length'] > 2.5 or r2['length'] / r1['length'] > 2.5:
                continue
            sim = calculate_similarity(r1['fingerprint'], r2['fingerprint'])
            if sim >= threshold:
                results.append({
                    "block1": f"{r1['path']}::{r1['name']}",
                    "block2": f"{r2['path']}::{r2['name']}",
                    "similarity": round(sim, 4)
                })
    
    results.sort(key=lambda x: x['similarity'], reverse=True)
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(results, f, indent=2)
            
    print("\n" + "="*80)
    print(f"🚀 Block-level Similarity Results (TOP 10 / Total Matches: {len(results)})")
    print("="*80)
    for idx, res in enumerate(results[:10]):
        print(f"RANK {idx+1}: {res['similarity']*100:.2f}% Match\n  A: {res['block1']}\n  B: {res['block2']}")
        
    return True

if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(description="AST-based Code Similarity Tool")
    parser_cli.add_argument("--dir", default="frontend/src", help="Directory to scan")
    parser_cli.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0.0 - 1.0)")
    parser_cli.add_argument("--min-len", type=int, default=10, help="Minimum AST node count")
    parser_cli.add_argument("--json", help="Path to save JSON report")
    args = parser_cli.parse_args()
    scan_codebase_similarity(args.dir, args.threshold, args.min_len, args.json)
