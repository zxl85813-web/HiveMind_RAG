# 📜 HiveMind Development Conventions: Shell & Placeholder Standards
> 本文档定义了系统中“空壳占位”代码的标准注释规范，以便于自动审计与未来补全。

---

## 1. 占位符标注规范 (SHELL Standard)

所有当前由于 MVP 阶段或依赖未就绪而存在的“空壳”函数、类或逻辑分支，必须使用以下统一格式进行标注：

### 格式
`# [SHELL: <FEATURE_ID>] Placeholder for <SHORT_DESCRIPTION>. Required for <TARGET_PHASE>.`

- **FEATURE_ID**: 对应的需求 ID (如 REQ-001) 或 模块 ID (如 M4.2)。
- **SHORT_DESCRIPTION**: 简短的功能描述。
- **TARGET_PHASE**: 预定的实施阶段 (如 Phase 5, Industrialization)。

### 示例
```python
def check_compliance(self, data):
    # [SHELL: REQ-104] Placeholder for complex regulatory check logic. Required for Phase 6.
    return True
```

---

## 2. 扫描与审计工具

开发人员可以使用以下命令快速扫描系统中的空壳：
`grep -r "\[SHELL:" .`

---

## 3. 常见的 SHELL 类型

- **Interface Shell**: 协议定义完成，但具体算法未填充。
- **Error Handle Shell**: 捕获了异常但仅记录日志，缺乏实质性的恢复逻辑。
- **Circuit Breaker Shell**: 预留了熔断挂钩，但判定阈值目前是硬编码的。
- **Policy Shell**: 预留了安全/质量策略接口，但目前默认返回 True。
