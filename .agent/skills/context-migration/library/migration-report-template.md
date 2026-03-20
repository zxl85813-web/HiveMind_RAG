# 迁移报告标准模板（Migration Report Template）

> 每次执行 context-migration skill 后，必须按此格式输出完整的迁移报告。
> 格式标准化的目的：让报告本身可以被存入 KI 系统，作为下次迁移的输入源。

---

## 📋 报告模板

```markdown
## 🧠 上下文迁移报告
> 迁移时间：{timestamp}  
> 信息源覆盖：KI({ki_count}条) / 对话摘要({conv_count}条) / TODO({todo_pending}个未完成)

---

### 1. 核心主轴（The North Star）

> 「这套对话系统到底在干什么」的一句话定义，以及「为什么这件事对用户重要」

**系统身份**：{project_one_liner}

**核心驱动力**：{why_it_matters_to_user}

**当前所处阶段**：{current_phase}（如：早期架构期 / 功能完善期 / 测试优化期）

---

### 2. 高权重概念与稳定偏好（Anchors）

#### 🔑 核心概念与术语
> 这些是项目专有的语言，必须沿用，不可自行造词

| 概念 | 含义 | 来源强度 |
|------|------|----------|
| {concept_1} | {definition} | 高（多次出现） |
| {concept_2} | {definition} | 中（明确定义过） |

#### ⚙️ 已形成的方法论与公式
> 这些是核心资产，不可随意替换

- {methodology_1}：{brief_description}
- {methodology_2}：{brief_description}

#### 🚫 禁区与反感点（Anti-patterns）
> 用户明确说过「不要这样」的模式，必须永久避开

- [ ] {antipattern_1}：{context}
- [ ] {antipattern_2}：{context}

#### 💬 语言气质与风格特征
- 深度期望：{depth_expectation}（如：技术细节要到代码级 / 架构层即可）
- 语言偏好：{language_style}（如：中文主体，技术术语保留英文）
- 结构偏好：{structure_style}（如：喜欢表格对比 / 喜欢分步骤 / 不喜欢流水账）

---

### 3. 当前进度与位置（Current Coordinates）

#### ✅ 最近已完成
- {completed_1}（对话：{conversation_title}）
- {completed_2}

#### 🔄 进行中 / 卡住的地方
- {in_progress_1}：当前状态 → {current_state}，卡点 → {blocker}
- {in_progress_2}

#### 📋 待办优先队列（来自 TODO.md）
1. **[最高优先]** {todo_1}
2. {todo_2}
3. {todo_3}

---

### 4. 后续接续策略（Continuation Strategy）

#### 🎯 新窗口最该先做的事
> 不是总结，是接续建议

1. **立即行动**：{immediate_action}
   - 为什么：{reasoning}
2. **本轮目标**：完成 {milestone}

#### 🛡️ 防衰退检查（Anti-regression Guards）
> 新窗口最容易在哪里跑偏，如何预防

- 风险点：{risk_1} → 防护：{guard_1}
- 风险点：{risk_2} → 防护：{guard_2}

---

### 5. 迁移质量自评（Transfer Quality Score）

> 对照接管公式自评：新窗口有效接管度 = 主轴重建 × 目标恢复度 × 偏好继承度 × 风格连续性 × 任务定位准确度

| 维度 | 自评分（1-5） | 说明 |
|------|-------------|------|
| 核心主轴重建 | {score}/5 | {comment} |
| 目标恢复度   | {score}/5 | {comment} |
| 偏好继承度   | {score}/5 | {comment} |
| 风格连续性   | {score}/5 | {comment} |
| 任务定位准确度 | {score}/5 | {comment} |
| **综合得分** | **{avg}/5** | {overall_comment} |

> 📌 如果任一维度 < 3 分，必须说明信息源不足的原因，并建议补充哪些额外上下文。
```

---

## 使用说明

1. **填写规则**：用实际内容替换 `{变量}` 占位符，删除所有 `{}` 标记
2. **长度控制**：完整报告应控制在约 800-1200 词之间，过长意味着没有提炼
3. **存档选项**：迁移报告可以保存到 `/docs/migration-logs/MIGRATION-{date}.md` 供后续参考
4. **自评诚实原则**：自评分必须如实填写，分数低说明需要补充信息源，不是说明工作做得差
