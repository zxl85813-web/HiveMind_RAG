# REQ-026: ChatBubble 一键复制消息 — 极微切片计划 (Micro-Plan)

> **对于 AI Agent:** 必须使用 `subagent-tdd-loop` 技能来逐个执行这些 Task。请按照 checkbox (`- [ ]`) 的顺序推进。

**目标:** 在组件库标准路径下通过 TDD 方式实现 ChatBubble 的复制到剪贴板功能。
**图谱锚点:** 
- `Requirement`: REQ-026
- `Design`: DES-026
- `Files`: 
  - `frontend/src/components/chat/ChatBubble.tsx` (Current Target)
  - `frontend/src/components/agents/ChatBubble.tsx` (Outdated Source)
---

### Task 1: 组件架构归位 (Path Normalization)

**涉及文件:**
- Create: `frontend/src/components/chat/ChatBubble.tsx`
- Remove: `frontend/src/components/agents/ChatBubble.tsx`
- Test: `frontend/tests/components/chat/ChatBubble.test.tsx` (Create if missing)

- [ ] **Step 1: Write the failing test (Red)**
  ```typescript
  import { render, screen } from '@testing-library/react';
  import { ChatBubble } from '@/components/chat/ChatBubble';

  test('should render ChatBubble in the correct directory', () => {
    render(<ChatBubble message={{ id: '1', role: 'swarm', content: 'Test' }} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
  ```

- [ ] **Step 2: 用本地基建运行它并期待失败**
  Run: `npm test frontend/tests/components/chat/ChatBubble.test.tsx`
  Expected: FAIL (Module not found)

- [ ] **Step 3: Write minimal implementation**
  Move existing code from `agents/` to `chat/` and update imports.

- [ ] **Step 4: Check & Pass (Green)**
  Run: `npm test`
  Expected: PASS

- [ ] **Step 5: Git Commit**
  Run: `git add . && git commit -m "refactor: moving ChatBubble to standard components/chat/ folder"`

---

### Task 2: 集成复制功能 TDD (Clipboard Feature)

**涉及文件:**
- Modify: `frontend/src/components/chat/ChatBubble.tsx`

- [ ] **Step 1: Write the failing test (Red)**
  ```typescript
  test('should call clipboard API when copy button clicked', async () => {
    const user = userEvent.setup();
    render(<ChatBubble message={{ id: '1', role: 'swarm', content: 'Copyable Content' }} />);
    const copyButton = screen.getByRole('button', { name: /copy/i });
    await user.click(copyButton);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Copyable Content');
  });
  ```

- [ ] **Step 2: 运行并期待失败**
  Run: `npm test`
  Expected: FAIL

- [ ] **Step 3: Write implementation**
  Verify/Implement `handleCopy` logic.

- [ ] **Step 4: Pass (Green)**
  Run: `npm test`
  Expected: PASS

---

### Task 3: 架构图谱自愈 (Graph Recalibration)

- [ ] **Step 1: Sync Graph**
  Run: `python .agent/skills/architectural-mapping/scripts/index_architecture.py`

- [ ] **Step 2: Verify Linkage**
  Run: `python .agent/skills/architectural-mapping/scripts/query_architecture.py --req "REQ-026"`
  Check if `DES-026` and the NEW file path are correctly mapped.

- [ ] **Step 3: Audit (Optional)**
  Run: `python .agent/checks/run_checks.ps1`
