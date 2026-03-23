/**
 * 🧪 [HMER Architecture Eval] 极限测试数据集 (Boundary Test Data Fixtures)
 * 目标: 提供非 happy-path 的脏数据、攻击载荷、巨型文本和编码边缘情况，
 * 验证解析器 (MultiTrackParser)、DOM 渲染器和数据库 (IndexedDB) 的强鲁棒性。
 */

// 1. 结构性脏数据 (解析器测试)
export const StreamAnomalies = {
    // 模拟被网络切断了一半的多字节 Unicode 字符 (例如 😂 被切开)
    SPLIT_UNICODE_CHUNK_1: new Uint8Array([0xF0, 0x9F]), 
    SPLIT_UNICODE_CHUNK_2: new Uint8Array([0x98, 0x82]),
    
    // 模拟损坏的 SSE Frame
    MALFORMED_JSON_EVENT: `data: {"id":"msg-1", "content":"hello", "thinking": "started \n\n`,
};

// 2. 极端边界文本 (DOM 渲染与安全测试)
export const ContentBoundaries = {
    // XSS 探针: 验证 React/Markdown 渲染器是否被注入
    XSS_PAYLOAD: `Hello! Here is a link: [Click Me](javascript:alert("XSS")) and an image ![alt]("onerror="alert('XSS')) \n\n <script>alert("XSS2")</script>`,
    
    // 超长无空格文本: 测试 CSS word-break 和 flex 容器是否被撑爆
    GIGANTIC_TOKEN: Array(5000).fill('A').join(''),
    
    // 深度嵌套 Markdown: 测试 remark/rehype 解析性能和递归爆炸
    DEEP_MARKDOWN_NESTING: `> Level 1\n>> Level 2\n>>> Level 3\n>>>> Level 4\n>>>>> Level 5\n>>>>>> Level 6\n>>>>>>> ${Array(100).fill('*Bold*').join(' ')}`,

    // Zalgo Text (Unicode 组合字符风暴): 测试字体渲染是否崩溃
    ZALGO_TEXT: `T̖O͇ I̘N̙V̫O͎K͍E̦ T͔H̞E͈ H͍I̥V̰Ḛ-M̦I̤N̪D R͍E̥P̰R͍E̦S̞E͈N̪T͔I̘N̙G̦ C̥H̞A͈O͇S̞.`,
    
    // 多语言混合与长 Emoji (RTL + CJK + Emoji)
    COMPLEX_MULTILINGUAL: `هذا اختبار 🐛 (Bug) 测试 💻 (Code) これは何ですか？ 🧑‍🔬👨‍🚀 family:`
};

// 3. 巨量状态模拟 (容量与虚拟滚动测试)
export const VolumeMocks = {
    // 快速生成包含 5000 条极长上下文的对话数据
    generateMassiveConversation: () => {
        return Array.from({ length: 5000 }).map((_, i) => ({
            id: `msg-vol-${i}`,
            role: i % 2 === 0 ? 'user' : 'assistant',
            content: i % 100 === 0 ? ContentBoundaries.COMPLEX_MULTILINGUAL : `Short message ${i}`,
            created_at: new Date(Date.now() - (5000 - i) * 1000).toISOString(),
            metadata: { token_count: 50 + (i % 200) }
        }));
    }
};
