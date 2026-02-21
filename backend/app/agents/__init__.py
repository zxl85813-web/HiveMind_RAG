"""
Agent 蜂巢集群。

只包含 Agent 定义和编排逻辑:
    - swarm.py       — Supervisor 编排器 (LangGraph)
    - base.py        — Agent 基类 (BaseAgent)
    - rag_agent.py   — RAG 检索增强 Agent
    - web_agent.py   — Web 搜索 Agent
    - code_agent.py  — 代码生成 Agent
    - reflection.py  — 自省/质量评估 Agent

⚠️ LLM 路由、记忆管理、MCP、Skills、学习引擎已迁至独立模块。

参见: REGISTRY.md > 后端 > agents 模块
"""
