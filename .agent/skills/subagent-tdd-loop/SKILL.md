---
name: subagent-tdd-loop
description: 基于 TDD 的微任务自动化执行器 (Subagent-Driven Development)，在当前会话中为每个任务派发隔离的子代理
---

# 🤖 Subagent TDD Loop (子代理 TDD 研发环)

通过为每一个微型开发任务分发全新、语境纯净的 Subagent (子代理) 来执行开发。并在每个任务完成后，进行严格的“双重验收”：先验 Spec (需求拟合度)，再验 Code Quality (代码质量门禁)。

**核心原则:** 纯净子代理 + 双阶段复核 = 高质量与防偏航。

## 什么时候使用它
当已经通过 `generate-micro-plan` 生成了拆分的微型任务列表（例如存在于 `TODO.md` 中）时，由主 Agent 调用此技能进入流水线。

## The Process (执行编排流程)

执行这套 SOP，主 Agent 不写业务代码，只做发牌官：

1. **提取信息**: 主控 Agent 从 `TODO.md` 中单独读取 Task N 的全部文本和上下文。
2. **派发子代工 (Implementer)**:
   - 告诉子代理："请按照这 5 步（写测试 -> 运行失败 -> 写实现 -> 运行通过 -> 提交）执行这个任务。"
   - 子代工作业完毕后需反馈其状态。
3. **Spec Review (合规审查)**: 
   - 检查该子代理写的代码是否完全符合上游设计要求，没有多写（YAGNI），也没有少写。
4. **Code Quality Review (质量门禁)**:
   - **强制**: 你必须在终端执行基础门禁脚本 `./.agent/checks/run_checks.ps1 <被修改的文件路径>`。
   - 只有通过 Lint、类型检查和测试用例绿灯，才能视为质量达标。
5. **归档**: 在 `TODO.md` 中给当前 Task 打钩 `[x]`，然后继续提取 Task N+1 循环此流程。

## ⚠️ 绝对禁忌 (Red Flags)

- **禁止跳过门禁**: 绝对不可以在没有运行 `./.agent/checks/run_checks.ps1` 或终端测试指令报错的情况下，强行进入下一个 Task。
- **禁止让子代理继承大量历史**: 发送给子任务代理的 Prompt 必须精准且有限（只有 Task 描述和图谱里该文件的上下文），避免历史 Token 污染。
- **遇到报错不硬拗**: 如果子代理尝试了 3 次仍无法修好终端报错，抛出给人类，不要进入死循环幻觉。

## 协同要求
- **输入来源**: 必须由 `generate-micro-plan` 技能生成合理的任务列表。
- **输出终点**: 任务归档后，可以选择通过 `openspec-archive-change` 归集本次的整个流水线变更。
