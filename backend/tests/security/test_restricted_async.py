from RestrictedPython import compile_restricted
from RestrictedPython.transformer import RestrictedPythonTransformer
import ast

class AsyncTransformer(RestrictedPythonTransformer):
    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)
    def visit_Await(self, node):
        return self.node_contents_visit(node)

code = "async def test(): await platform.call('test')"
# Test if we can compile it with standard compile_restricted
try:
    compile_restricted(code, "<test>", "exec")
    print("Success")
except Exception as e:
    print(f"Failed: {e}")
