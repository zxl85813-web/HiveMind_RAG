"""
共享记忆系统。

记忆层次:
    1. 工作记忆 (working.py)  — 短期, Redis
    2. 情景记忆 (episodic.py) — 中期, 对话摘要
    3. 语义记忆 (semantic.py) — 长期, 向量检索
    4. 共享 TODO (todo.py)    — 任务队列

管理器: manager.py

参见: REGISTRY.md > 后端 > memory 模块
"""
