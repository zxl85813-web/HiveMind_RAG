---
name: 🤖 AI Blocked Report (AI 阻滞报告)
about: [内部自动生成] 由 Agent/Skill 在执行任务受阻时自动提单
title: "[BLOCKED] AI 任务执行受阻: {简述}"
labels: 'blocked, ai-generated'
assignees: ''
---

## 🛑 阻塞说明 (Blocker Summary)

<!-- AI 将在此描述为何无法继续执行原任务 -->
**原案 Issue:** #XXX
**执行 Skill:** (例如 `generate-tests`, `opsx-apply`)

## 👥 协作者分配 (Collaborator Assignment)

- 协作者 (必填):
	- [ ] `zxl85813-web` (Owner)
	- [ ] `Uchihacc` (Collaborator)
- GitHub Assignee (必填): `@<username>`
- 复核人 (可选): `@<username>`

## 🧠 Skill 指定 (Skill Routing)

- 主 Skill (必填): `skills/<name>`
- 关联 Skill (可选): `skills/<name>`

## 🔍 问题分析 (Technical Details)

<!-- 报错日志或技术瓶颈 -->
```text
(AI 填写的相关日志)
```

## 🛠️ 寻求人类解决建议 (Required Actions for Humans)

<!-- AI 将指出它需要人类做什么才能继续。例如：
1. 需要人类在 SQLModel 中增加一段缺失的 metadata 映射。
2. 由于外部包版本冲突，需要调整 poetry.lock 依赖。 
-->
- [ ] ...

## 🏷️ 建议标签 (Domain Allocation)
- [ ] `frontend` / `backend` / `infra`

*(本 Issue 由 Agent 遵循 `team-collaboration-standards.md` 第 4.2 节自动发起)*
