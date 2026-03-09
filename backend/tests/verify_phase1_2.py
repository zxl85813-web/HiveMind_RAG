import asyncio
import os
import sys

# Force UTF-8 for windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add project root and backend to path
cwd = os.getcwd()
sys.path.append(cwd)
sys.path.append(os.path.join(cwd, "backend"))


async def test_agentic_search():
    print("--- [TASK 1] Testing Agentic Search Tools ---")
    try:
        from backend.app.agents.agentic_search import grep_search, list_files_recursive

        # 1. list_files_recursive
        print("[1/3] Testing list_files_recursive...")
        res1 = await list_files_recursive.ainvoke({"directory": ".", "pattern": "*.md", "max_depth": 1})
        print(f"Result (truncated): {res1[:50]}...")

        # 2. grep_search
        print("[2/3] Testing grep_search...")
        res2 = await grep_search.ainvoke({"query": "HiveMind", "file_pattern": "README.md"})
        print(f"Result (truncated): {res2[:50]}...")

    except Exception as e:
        print(f"ERROR in Agentic Search: {e}")


async def test_native_tools():
    print("\n--- [TASK 2] Testing Native Tools ---")
    try:
        # Mocking loguru and other deps to avoid failures if not installed
        import unittest.mock as mock

        sys.modules["loguru"] = mock.MagicMock()
        sys.modules["langchain_core"] = mock.MagicMock()
        sys.modules["app.agents.memory"] = mock.MagicMock()
        sys.modules["app.models.agents"] = mock.MagicMock()
        sys.modules["app.services.retrieval"] = mock.MagicMock()

        from backend.app.agents.tools import python_interpreter, search_available_tools, think

        # 1. think
        print("[1/3] Testing think...")
        res1 = await think.run({"thought": "Validating the thinking process.", "target_goal": "Verification"})
        print(f"Result: {res1}")

        # 2. search_available_tools
        print("[2/3] Testing search_available_tools...")
        res2 = await search_available_tools.run({"query": "database"})
        print(f"Result: {res2}")

        # 3. python_interpreter
        print("[3/3] Testing python_interpreter...")
        code = "x = [1, 2, 3]; print(f'REPL Test: {x}')"
        res3 = await python_interpreter.run({"code": code})
        print(f"Result: {res3}")

    except Exception as e:
        print(f"ERROR in Native Tools: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_agentic_search())
        loop.run_until_complete(test_native_tools())
    except Exception as e:
        print(f"GLOBAL ERROR: {e}")
    finally:
        print("\n--- Verification Completed ---")
