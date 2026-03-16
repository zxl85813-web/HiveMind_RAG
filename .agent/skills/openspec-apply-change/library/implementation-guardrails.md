# 🛡️ 实施守则 (Implementation Guardrails)

## 1. 最小变更原则 (Minimal Impact)
- 每次仅执行一个任务。
- 禁止修改与当前任务无关的代码文件。
- 如果发现不得不修改多处，考虑是否需要重新分解任务。

## 2. 闭环自检机制 (Loopback Verification)
- 每一项任务 `- [x]` 标记完成后，必须运行该任务对应的验证命令（Verification Command）。
- 禁止在验证失败的情况下跳到下一个任务。

## 3. 架构锚点 (Architectural Anchors)
- 在编码前，必须确认该文件的架构定位（Service? Controller? Model?）。
- 遵守项目定义的 Pydantic V2 或 TS 强类型契约。

## 4. 报错处理策略
- 如果出现编译错误或测试失败，首先尝试自主修复。
- 如果修复耗时超过 2 次转圈，必须汇报给用户，并提供可选方案。
