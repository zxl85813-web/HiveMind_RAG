import tree_sitter_typescript as ts
from tree_sitter import Language, Parser, Query

TSX_LANGUAGE = Language(ts.language_tsx())
parser = Parser(TSX_LANGUAGE)

query_string = """
(function_declaration name: (identifier) @name) @block
"""
query = Query(TSX_LANGUAGE, query_string)

content = b"function Test() { return <div />; }"
tree = parser.parse(content)
captures = query.captures(tree.root_node)
print(f"Captures: {len(captures)}")
for node, tag in captures:
    print(f"  - Tag: {tag}, Node: {node.type}")
