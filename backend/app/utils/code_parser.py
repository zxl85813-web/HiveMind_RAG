import ast
import os
from typing import Any, Dict, List

class CodeStructureParser:
    """
    M7.2.3: AST Parser for extracting Code Assets.
    Identifies classes, functions, and docstrings for structural indexing.
    """
    @staticmethod
    def parse_python(file_path: str) -> Dict[str, Any]:
        """Parse Python file using AST."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception as e:
            return {"error": f"Failed to parse AST: {str(e)}"}

        structures = {
            "classes": [],
            "functions": [],
            "imports": [],
            "docstring": ast.get_docstring(tree)
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                structures["classes"].append({
                    "name": node.name,
                    "docstring": ast.get_docstring(node),
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                    "lineno": node.lineno
                })
            elif isinstance(node, ast.FunctionDef):
                # Avoid top-level duplicated methods if we already got them in classes
                structures["functions"].append({
                    "name": node.name,
                    "docstring": ast.get_docstring(node),
                    "args": [arg.arg for arg in node.args.args],
                    "lineno": node.lineno
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                structures["imports"].append(ast.dump(node))

        return structures

    @staticmethod
    def is_code_file(file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in [".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".sql"]
