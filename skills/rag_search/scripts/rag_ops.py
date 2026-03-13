import sys
import os
import asyncio
import argparse
import json
from pathlib import Path

# 强制设置 UTF-8 编码，防止 Windows 控制台输出中文报错
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 将项目根目录和 backend 目录加入路径，确保能导入 app
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.append(str(ROOT_DIR / "backend"))

# 模拟环境变量，防止某些模块初始化失败
os.environ["MOCK_LLM"] = "true" 

async def run_analysis(query: str):
    """调用后端 Pre-processing 逻辑分析查询"""
    # 延迟导入以避免循环引用
    from app.services.retrieval.preprocessing import QueryPreProcessingStep
    from app.services.retrieval.protocol import RetrievalContext
    
    ctx = RetrievalContext(query=query, kb_ids=[])
    step = QueryPreProcessingStep(use_hyde=True, rewrite_query=True, decompose_query=True)
    
    print(f"[*] Analyzing query: {query}")
    await step.execute(ctx)
    
    result = {
        "original_query": ctx.query,
        "expanded_queries": ctx.expanded_queries,
        "sub_queries": getattr(ctx, "sub_queries", []),
        "logs": ctx.trace_log
    }
    return result

def format_citations(results_json):
    """格式化引用来源的辅助逻辑"""
    data = json.loads(results_json)
    output = []
    output.append("## 来源")
    for i, res in enumerate(data, 1):
        source = res.get("metadata", {}).get("source", "未知来源")
        score = res.get("score", 0)
        output.append(f"[{i}] {source} (相关度: {score:.2f})")
    return "\n".join(output)

async def main():
    parser = argparse.ArgumentParser(description="HiveMind RAG Operations Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--query", required=True, help="User query to analyze")
    
    # Cite command
    cite_parser = subparsers.add_parser("cite")
    cite_parser.add_argument("--results", required=True, help="JSON string of search results")

    args = parser.parse_args()
    
    if args.command == "analyze":
        res = await run_analysis(args.query)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "cite":
        print(format_citations(args.results))
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
