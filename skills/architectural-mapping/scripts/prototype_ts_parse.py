import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser
from pathlib import Path

# 1. 核心配置：加载 TSX 语言 (能够处理 React 代码)
TSX_LANGUAGE = Language(ts_typescript.language_tsx())
parser = Parser(TSX_LANGUAGE)

def analyze_tsx(file_path):
    print(f"Analyzing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 2. 解析为语法树
    tree = parser.parse(bytes(content, "utf8"))
    
    # 3. 定义 S-Expression 查询
    # 使用正确的 TSX 节点名称
    from tree_sitter import Query, QueryCursor
    query_string = """
    (function_declaration
      name: (identifier) @component_name)

    (variable_declarator
      name: (array_pattern 
        (identifier) @state_name
        (identifier) @setter_name)
      value: (call_expression
        function: (identifier) @hook_name
        (#eq? @hook_name "useState")))

    (jsx_opening_element
      name: [
        (identifier) @tag_name
        (member_expression) @tag_name
      ])
    """
    
    query = Query(TSX_LANGUAGE, query_string)
    # 0.25+ API: QueryCursor(query).captures(node)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    
    # 4. 处理结果 (字典格式: { "tag": [node1, node2, ...] })
    results = {
        "components": [node.text.decode("utf8") for node in captures.get("component_name", [])],
        "states": [node.text.decode("utf8") for node in captures.get("state_name", [])],
        "tags": {node.text.decode("utf8") for node in captures.get("tag_name", [])}
    }

    # 5. 输出展示
    print(f"Components Found: {results['components']}")
    print(f"States Found: {results['states']}")
    print(f"Unique JSX Tags: {sorted(list(results['tags']))}")

if __name__ == "__main__":
    # 测试 App.tsx
    sample_file = Path(r"c:\Users\linkage\Desktop\aiproject\frontend\src\App.tsx")
    if sample_file.exists():
        analyze_tsx(sample_file)
    else:
        print("Sample file not found!")
