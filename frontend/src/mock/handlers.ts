import * as data from './mockData';

export const mockHandlers: Record<string, any> = {
    // Knowledge
    'GET:/knowledge': { success: true, data: data.mockKBs, message: 'Success' },
    'POST:/knowledge': { success: true, data: data.mockKBs[0], message: 'Knowledge base created successfully' },
    'GET:/knowledge/kb-001': { success: true, data: data.mockKBs[0], message: 'Success' },
    'GET:/knowledge/kb-001/documents': {
        success: true, data: [
            { id: 'doc-001', filename: 'HiveMind_System_Design.pdf', file_type: 'pdf', file_size: 2048576, status: 'indexed', created_at: new Date().toISOString() },
            { id: 'doc-002', filename: 'Multi_Agent_Swarm_Specs.docx', file_type: 'docx', file_size: 1024567, status: 'indexed', created_at: new Date().toISOString() },
            { id: 'doc-003', filename: 'API_Contract_Draft.md', file_type: 'md', file_size: 45678, status: 'pending', created_at: new Date().toISOString() }
        ], message: 'Success'
    },

    // Agents
    'GET:/agents/swarm/agents': { success: true, data: data.mockAgents, message: 'Success' },
    'GET:/agents/swarm/stats': { success: true, data: data.mockStats, message: 'Success' },
    'GET:/agents/swarm/todos': { success: true, data: data.mockTodos, message: 'Success' },
    'GET:/agents/swarm/reflections': { success: true, data: data.mockReflections, message: 'Success' },
    'GET:/agents/swarm/traces': { success: true, data: data.mockTraces, message: 'Success' },

    // Learning
    'GET:/learning/discoveries': { success: true, data: data.mockDiscoveries, message: 'Success' },
    'GET:/learning/subscriptions': {
        success: true, data: [
            { id: 'sub-1', topic: 'LangGraph', created_at: new Date().toISOString() },
            { id: 'sub-2', topic: 'Ant Design X', created_at: new Date().toISOString() }
        ], message: 'Success'
    },
    'POST:/learning/daily-cycle': {
        success: true,
        data: {
            report_date: new Date().toISOString().slice(0, 10),
            report_path: `docs/learning/daily/${new Date().toISOString().slice(0, 10)}.md`,
            local_materials_count: 7,
            github_project_items_count: 6,
            github_issues_count: 8,
            agent_summary: '学习信号显示重点在 RAG 与 Agent 编排，建议优先做质量闭环与多厂商对照。',
            learning_tracks: ['RAG 与检索质量', 'Agent 编排与自治', '评测与质量工程'],
            suggestions: [
                {
                    title: '建立每日回归学习卡片',
                    reason: '项目中持续出现测试与回归相关任务。',
                    action: '将当天变更映射到最小回归测试，并在次日复盘。',
                },
            ],
        },
        message: 'Daily learning cycle completed',
    },
    'GET:/learning/daily-reports': {
        success: true,
        data: [
            `docs/learning/daily/${new Date().toISOString().slice(0, 10)}.md`,
            'docs/learning/daily/2026-03-08.md',
        ],
        message: 'Success',
    },
    'GET:/learning/daily-report-content': {
        success: true,
        data: {
            report_path: `docs/learning/daily/${new Date().toISOString().slice(0, 10)}.md`,
            content: [
                `# Self Learning Report - ${new Date().toISOString().slice(0, 10)}`,
                '',
                '## 多元外部学习信号（X + AI 大厂 + 重点开源）',
                '- [OpenAI News](https://openai.com/news/rss.xml)',
                '- [Anthropic News](https://www.anthropic.com/news)',
                '- [Google DeepMind Blog](https://deepmind.google/discover/blog/)',
                '- [x.com/OpenAI](https://x.com/OpenAI)',
                '',
                '## 系统改进建议',
                '1. 建立多厂商方案对照学习卡',
            ].join('\n')
        },
        message: 'Success'
    },

    // Chat / Memory
    'GET:/chat/conversations': {
        success: true, data: [
            { id: 'conv-1', title: '探讨 Agent 自省机制', last_message_preview: '目前的逻辑已经闭环...', updated_at: new Date().toISOString() },
            { id: 'conv-2', title: '知识库导入问题', last_message_preview: '请检查文件的编码格式', updated_at: new Date().toISOString() }
        ], message: 'Success'
    },

    // Audit
    'GET:/audit/queue': { success: true, data: data.mockReviews, message: 'Success' },
    'POST:/audit/rev-1/approve': { success: true, data: { ...data.mockReviews[0], status: 'approved' }, message: 'Approved' },
    'POST:/audit/rev-1/reject': { success: true, data: { ...data.mockReviews[0], status: 'rejected' }, message: 'Rejected' },

    // Evaluation
    'GET:/evaluation/testsets': { success: true, data: data.mockEvalSets, message: 'Success' },
    'GET:/evaluation/reports': { success: true, data: data.mockReports, message: 'Success' },
    'GET:/evaluation/badcases': { success: true, data: data.mockBadCases, message: 'Success' },
    'POST:/evaluation/testset': { success: true, data: 'task_id_123', message: 'Testset generation started' },
    'POST:/evaluation/set-finance/evaluate': { success: true, data: 'task_id_456', message: 'Evaluation started' },

    // Knowledge Graph
    'GET:/knowledge/kb-001/graph': { success: true, data: data.mockGraphData, message: 'Success' },

    // Batch Jobs
    'GET:/agents/batch/jobs': { success: true, data: data.mockBatchJobs, message: 'Success' },
    'GET:/agents/batch/jobs/job-001': { success: true, data: data.mockBatchJobs[0], message: 'Success' },
    'GET:/agents/batch/jobs/job-002': { success: true, data: data.mockBatchJobs[1], message: 'Success' },

    // MCP & Skills (Settings page)
    'GET:/agents/mcp/status': {
        success: true, data: [
            { name: 'filesystem', status: 'connected', type: 'stdio', command: 'npx', args: ['-y', '@anthropic/mcp-filesystem'] },
            { name: 'web-search', status: 'disconnected', type: 'stdio', command: 'npx', args: ['-y', '@anthropic/mcp-web-search'] },
        ], message: 'Success'
    },
    'GET:/agents/mcp/tools': {
        success: true, data: [
            { name: 'read_file', description: 'Read contents of a file from the filesystem' },
            { name: 'write_file', description: 'Write content to a file on the filesystem' },
            { name: 'list_directory', description: 'List files and directories at a given path' },
            { name: 'web_search', description: 'Search the web for information' },
        ], message: 'Success'
    },
    'GET:/agents/skills': {
        success: true, data: [
            { name: 'rag_qa', version: '1.0.0', description: 'Knowledge base Q&A with citation', status: 'active' },
            { name: 'doc_summary', version: '1.0.0', description: 'Summarize long documents', status: 'active' },
            { name: 'code_review', version: '0.9.0', description: 'Review code quality and suggest improvements', status: 'inactive' },
        ], message: 'Success'
    },

    // Platform Knowledge (Settings page)
    'GET:/settings/platform-knowledge': {
        overview: '本系统是 **HiveMind** — 一个企业级 AI-First RAG 平台。',
        features: [
            { name: '知识库管理', path: '/knowledge', description: '创建和管理知识库，上传文档(PDF/DOCX/MD/TXT)。', operations: ['创建知识库', '上传文档', '管理标签'] },
            { name: 'RAG 评测中心', path: '/evaluation', description: '对知识库的检索质量进行量化评测。', operations: ['创建评测集', '运行评测'] },
            { name: '安全中心', path: '/security', description: '文档脱敏策略管理，PII 检测。', operations: ['配置脱敏规则'] },
            { name: 'Agent 蜂巢', path: '/agents', description: '查看和监控 AI Agent 集群状态。', operations: [] },
        ],
        faq: [
            { q: '如何创建知识库？', a: '在聊天中输入「创建知识库」，或导航到知识库管理页面。' },
            { q: '支持哪些文档格式？', a: '支持 PDF、DOCX、Markdown、TXT 格式。' },
        ],
    },
    'PUT:/settings/platform-knowledge': {
        overview: 'Updated', features: [], faq: [],
    },

    // Security — 脱敏策略
    'GET:/security/policies': {
        success: true, data: [
            {
                id: 1, name: '默认企业脱敏策略', description: '覆盖身份证、手机号、银行卡、邮箱等常见敏感信息',
                is_active: true,
                rules_json: JSON.stringify([
                    { type: 'id_card', action: 'mask', enabled: true },
                    { type: 'phone', action: 'mask', enabled: true },
                    { type: 'email', action: 'mask', enabled: true },
                    { type: 'bank_card', action: 'mask', enabled: true },
                ]),
                created_at: '2026-01-15T08:00:00Z', updated_at: '2026-02-20T10:30:00Z',
            },
            {
                id: 2, name: '最小化脱敏策略', description: '仅检测身份证号，适用于内部文档',
                is_active: false,
                rules_json: JSON.stringify([
                    { type: 'id_card', action: 'mask', enabled: true },
                ]),
                created_at: '2026-02-01T09:00:00Z', updated_at: '2026-02-01T09:00:00Z',
            },
            {
                id: 3, name: '严格审计策略', description: '全类型检测 + 替换模式，适用于对外发布文档',
                is_active: false,
                rules_json: JSON.stringify([
                    { type: 'id_card', action: 'replace', enabled: true },
                    { type: 'phone', action: 'replace', enabled: true },
                    { type: 'email', action: 'replace', enabled: true },
                    { type: 'bank_card', action: 'replace', enabled: true },
                    { type: 'address', action: 'replace', enabled: true },
                    { type: 'name', action: 'replace', enabled: true },
                ]),
                created_at: '2026-02-10T14:00:00Z', updated_at: '2026-02-10T14:00:00Z',
            },
        ], message: 'Success'
    },

    // Security — 检测器
    'GET:/security/detectors': {
        success: true, data: {
            available_detectors: [
                { type: 'id_card', description: '中国大陆居民身份证号码检测 (18位)', regex: '\\d{17}[\\dXx]' },
                { type: 'phone', description: '中国大陆手机号码检测 (11位)', regex: '1[3-9]\\d{9}' },
                { type: 'email', description: '电子邮箱地址检测', regex: '[\\w.-]+@[\\w.-]+\\.\\w+' },
                { type: 'bank_card', description: '银行卡号检测 (16-19位)', regex: '\\d{16,19}' },
                { type: 'address', description: '中国大陆物理地址检测 (NER模型)', regex: 'Custom Logic' },
            ]
        }, message: 'Success'
    },

    // Security — 审计日志
    'GET:/security/audit/logs': {
        success: true, data: [
            { id: 'log-1', user_id: 'user-001', action: 'grant_permission', resource_type: 'document', resource_id: 'doc-001', details: '{"permission": "read", "target_user": "analyst-01"}', timestamp: '2026-02-28T09:15:00Z' },
            { id: 'log-2', user_id: 'user-001', action: 'create_policy', resource_type: 'security_policy', resource_id: '3', details: '{"name": "严格审计策略"}', timestamp: '2026-02-28T08:30:00Z' },
            { id: 'log-3', user_id: 'user-001', action: 'activate_policy', resource_type: 'security_policy', resource_id: '1', details: '{"name": "默认企业脱敏策略"}', timestamp: '2026-02-27T16:00:00Z' },
            { id: 'log-4', user_id: 'user-001', action: 'upload_document', resource_type: 'document', resource_id: 'doc-003', details: '{"filename": "API_Contract_Draft.md"}', timestamp: '2026-02-27T14:22:00Z' },
            { id: 'log-5', user_id: 'user-001', action: 'revoke_permission', resource_type: 'document', resource_id: 'doc-002', details: '{"perm_id": "perm-005"}', timestamp: '2026-02-26T11:00:00Z' },
            { id: 'log-6', user_id: 'user-001', action: 'create_kb', resource_type: 'knowledge_base', resource_id: 'kb-001', details: '{"name": "企业制度知识库"}', timestamp: '2026-02-25T09:00:00Z' },
            { id: 'log-7', user_id: 'user-001', action: 'login', resource_type: 'session', resource_id: 'sess-101', details: '{"ip": "192.168.1.100"}', timestamp: '2026-02-25T08:55:00Z' },
        ], message: 'Success'
    },

    // Security — ACL
    'GET:/security/permissions/document/doc-001': {
        success: true, data: [
            { id: 'perm-1', document_id: 'doc-001', grantee_type: 'user', grantee_id: 'analyst-01', permission_level: 'read', granted_by: 'user-001', created_at: '2026-02-20T10:00:00Z' },
            { id: 'perm-2', document_id: 'doc-001', grantee_type: 'role', grantee_id: 'admin', permission_level: 'write', granted_by: 'user-001', created_at: '2026-02-18T09:00:00Z' },
        ], message: 'Success'
    },
    'POST:/security/permissions': { success: true, data: { id: 'perm-new' }, message: 'Permission granted' },
    'POST:/security/policies': {
        success: true, data: { id: 4, name: 'New Policy', is_active: false, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, message: 'Created'
    },
};

export const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
