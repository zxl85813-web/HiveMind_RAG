# Root Cause Tracing (回溯追踪)

## 核心哲学
Bug 往往表现在调用栈的最深处（如：由于路径不对导致 git init 失败）。你的直觉是修复报错的那一行，但这只是在治疗症状。

**原则**：沿着调用链向后追溯，直到找到原始触发点，然后在源头进行修复。

## 追踪流程 (The Tracing Process)

1. **观察症状**：`Error: git init failed in /packages/core`
2. **寻找直接诱因**：是哪行代码执行了 `git init`？参数是什么？
3. **追问：谁调用了它？**
   - `Manager.init()` -> 被 `Session.start()` 调用 -> 被 `Test.setup()` 调用。
4. **检查传递的值**：
   - 发现传递的 `projectDir` 是空字符串 `""`。
   - 为什么是空字符串？
5. **定位原始触发点**：
   - 发现由于测试配置错误，变量在 `beforeEach` 执行前就被访问了。
   - **根因**：顶层变量初始化顺序错误。

## 栈追踪技巧 (Stack Trace Tips)
- **增加检测点**：在报错代码前一行，手动加入 `new Error().stack` 并打印。
- **使用系统 stderr**：在测试中建议直接用 `console.error` 打印，防止被日志框架过滤。
- **包含上下文**：打印变量时，顺便打印 `process.cwd()` 和环境变量，这些往往是隐性根因。

---

# Defense-in-Depth (深度防御校验)

## 核心哲学
当你修复了一个由于数据非法导致的 Bug 时，在报错点加个判断是不够的。这个校验可能会被其他调用路径绕过。

**原则**：在数据流经的**每一个层级**都加上校验。让这个 Bug 在结构上变得不再可能发生。

## 四道防线 (The Four Layers)

1. **第一层：入口校验 (Entry Point)**
   - 在 API 边界直接拦截。例如：`if (!dir) throw new Error('path required')`。
2. **第二层：业务逻辑校验 (Business Logic)**
   - 确保数据逻辑合理。例如：校验路径是否真的在 `/tmp` 目录下。
3. **第三层：环境守卫 (Environment Guards)**
   - 防止由于环境冲突导致的破坏。例如：在测试环境下，禁止操作非临时目录。
4. **第四层：调试监测 (Debug Instrumentation)**
   - 即使所有校验都失效，也必须有详细的 Context Log 供事后复盘。

## 落地案例
**Bug**: 空路径导致在源码目录误删文件。
**四层防御**:
- Layer 1: 函数入口判断路径不为空。
- Layer 2: 逻辑层判断路径必须包含特定前缀。
- Layer 3: 环境层监测 `NODE_ENV === 'test'` 时，若路径不包含 `temp` 则强制报错。
- Layer 4: 执行删除动作前打印全路径和堆栈。
