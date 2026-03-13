# 📜 架构图谱使用规范

> **原则**: 凡涉及结构性变更（修改核心逻辑、重构、删除代码），必须先询问“软件大脑”。

## 1. 强制性行为
- **自省优先**: 在响应用户重构请求前，AI Agent 必须调用 `query_architecture.py` 获取当前受影响的节点。
- **关联补全**: 在创建新测试或新设计时，必须在文档/代码中显式标记关联项（如 `@covers REQ-XXX`, `@specifies DES-XXX`），以便索引器自动捕获。
- **状态同步**: 任何导致目录结构、Skill 增减的变更，必须在任务结束前运行 `index_architecture.py` 刷新图谱。

## 2. 路由逻辑建议
- **精准读码**: AI Agent 应根据图谱返回的 `files` 列表进行多线程读取，禁止在不确定的情况下对 `backend/app` 进行递归扫描以节省 Tokens。
- **影子检查**: 如果发现代码中存在图谱未记录的关系，Agent 应主动报告并更新 `index_architecture.py` 的解析逻辑。

## 3. 标准化标签
- `@covers REQ-NNN`: 测试代码关联需求。
- `@specifies DES-NNN`: 设计文档关联设计单。
- `@implements APP/PATH`: 代码实现文件路径映射。

---
*Created by Antigravity AI | 2026-03-13*
