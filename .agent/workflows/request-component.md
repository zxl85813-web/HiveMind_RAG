---
description: 发现缺失通用组件或工具时，上报并请求标准库支援的标准流程
---

# 🚀 请求构建新通用组件 / 工具流程 (Component/Util Request)

> **触发时机**: 当你在开发一个功能块时发现，某个 UI 交互 (如"密码强度评分条") 或某个后端工具函数 (如"解析嵌套字典的路径键") 并不存在于 `.agent/rules/component-inventory.md` 或 `.agent/rules/backend-utilities-inventory.md` 中，但你强烈觉得它具备复用价值。
>
> **重要原则**: 不要因为一时之便，私自在这个业务模块下写死只用一次的硬编码。

## 📋 申请步骤

### Step 1: 停下手头工作，确认其普适性
- 【前端 Component】: 这个东西会不会在另外 2 个及以上的页面被用到？是不是有别于强关联特定 Domain 的逻辑代码？
- 【后端 Util】: 这个函数是不是只要输入参数，就一定能算出纯净的结果，而且和当前的数据库 Session 没有半毛钱耦合？

### Step 2: 在当前界面的 TODO.md 追加记录
打开项目根目录下的 `TODO.md`，并在 「推迟 / 搁置的事项」区域（或者对应的后端/前端 Feature Area）追加申请条目。

- **如果你需要一个前端被复用的 Component，写**: 
  `- [ ] 🔧 COMPONENT_NEEDED: [名称: 如 PasswordStrengthMeter] - [用途: 显示复杂度的评分条]`
- **如果你需要一个后端的工具 Util 函数，写**:
  `- [ ] 🔧 UTIL_NEEDED: [名称: 如 nested_dict_get] - [用途: 解析 JSON 路径点号格式的值]`

### Step 3: 回到当前开发上下文，使用 "伪装替换" (Mock/Fallback)
为了不让当前的系统宕机，或者你自己这边的流程被卡死。
- 前端：先用简单的 `<div className="wip">[密码强度评分条 Placeholder]</div>` 暂代。
- 后端：先直接以一种粗糙的方法实现计算。注释中标注 `# TODO: Replace with UTIL_NEEDED: nested_dict_get`。

### Step 4: 等待架构师/Reviewer 审批并打磨上线
当版本里程碑到来并执行 `code-review.md` 自省时，所有的 `🔧 COMPONENT_NEEDED` 和 `🔧 UTIL_NEEDED` 都会被统计出。
由专人或 AI Agent 将其补满，然后进入 `common/` 或 `utils/`，最后发版供所有人使用。
