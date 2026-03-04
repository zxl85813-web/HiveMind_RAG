// 1. Knowledge Base Mock Data (25 records for scrolling/pagination)
export const mockKBs = Array.from({ length: 25 }).map((_, i) => ({
    id: `kb-${(i + 1).toString().padStart(3, '0')}`,
    name: i === 0 ? 'HiveMind 核心架构 (Primary)' : `测试知识库-数据分步-${i + 1}`,
    description: `这是第 ${i + 1} 个测试知识库，用于验证前端列表在大量数据下的渲染性能。其包含 ${Math.floor(Math.random() * 100)} 份模拟文档。`,
    embedding_model: i % 2 === 0 ? 'text-embedding-3-small' : 'text-embedding-3-large',
    created_at: new Date(Date.now() - i * 86400000).toISOString(),
    updated_at: new Date(Date.now() - i * 3600000).toISOString(),
    owner_id: 'user-001',
    is_public: i < 5,
    vector_collection: `coll_${(i + 1).toString().padStart(3, '0')}`
}));

// 2. Agents Mock Data (Full Team)
export const mockAgents = [
    { name: 'Supervisor', description: '集群总控编排器，负责复杂任务分解与全局状态监控', status: 'idle', icon: '🐝' },
    { name: 'RAG-Specialist', description: '知识库检索专家，负责 Hybrid Search 与 Rerank 优化', status: 'processing', icon: '📚' },
    { name: 'Code-Architect', description: '代码生成专家，精通多语言高性能系统架构设计', status: 'idle', icon: '🏗️' },
    { name: 'Critic-Agent', description: '质量与合规性审查 Agent，负责生成的最后一道防线', status: 'reflecting', icon: '⚖️' },
    { name: 'Discovery-Bot', description: '开源情报搜集器，负责监控 GitHub/Reddit 技术趋势', status: 'idle', icon: '🔭' }
];

// 3. Reflection Logs (60 records for pagination/volume tests)
export const mockReflections = Array.from({ length: 60 }).map((_, i) => ({
    id: `refl-${i + 1}`,
    agent_name: mockAgents[i % 5].name,
    type: ['strategy_refinement', 'self_correction', 'information_gathering', 'risk_assessment'][i % 4],
    summary: `第 ${i + 1} 条自省洞察: 成功处理了关于${['语义偏移', '响应超时', '逻辑闭环', '权限冲突'][i % 4]}的潜在风险。`,
    details: {
        input_tokens: 1024 + i,
        output_tokens: 512 + i,
        trace_id: `trace-uuid-${i}`
    },
    confidence_score: 0.85 + Math.random() * 0.1,
    action_taken: i % 2 === 0 ? '自动优化 Prompt 策略' : '已通知 Supervisor 人工介入',
    created_at: new Date(Date.now() - i * 900000).toISOString()
}));

// 4. Shared TODOs (15 tasks)
export const mockTodos = Array.from({ length: 15 }).map((_, i) => ({
    id: `t-${i + 1}`,
    title: `${['[核心]', '[维护]', '[测试]', '[实验]'][i % 4]} 任务批次 #${i + 1}`,
    description: `这是一个自动生成的模拟任务描述。具体内容涉及${['集群稳定性提升', '文档模型对齐', '向量库迁移', 'UI/UX 微调'][i % 4]}。`,
    priority: i < 3 ? 'critical' : i < 6 ? 'high' : i < 10 ? 'medium' : 'low',
    status: i < 2 ? 'in_progress' : i < 8 ? 'pending' : i < 12 ? 'completed' : 'waiting_user',
    created_by: 'Supervisor',
    assigned_to: i % 2 === 0 ? mockAgents[i % 5].name : 'Admin',
    created_at: new Date(Date.now() - i * 43200000).toISOString()
}));

// 5. Tech Discoveries (Learning)
export const mockDiscoveries = Array.from({ length: 24 }).map((_, i) => ({
    id: `disc-${i + 1}`,
    title: `${['Next.js 15', 'LangGraph.js v1', 'DeepSeek-V3', 'FastAPI 0.115'][i % 4]} 深度解析 #${i + 1}`,
    summary: '检测到外部开源社区在此领域有重大进展。该项目的新特性在高并发处理和内存管理方面表现卓越，建议系统性评估。',
    category: ['framework', 'ai_model', 'database', 'tooling'][i % 4],
    relevance_score: 0.65 + Math.random() * 0.3,
    url: 'https://github.com/trending',
    discovered_at: new Date(Date.now() - i * 14400000).toISOString()
}));

// 6. Stats Summary
export const mockStats = {
    active_agents: 5,
    today_requests: 256,
    shared_todos: 15,
    reflection_logs: 60
};
// 7. Audit Mock Data
export const mockReviews = Array.from({ length: 5 }).map((_, i) => ({
    id: `rev-${i + 1}`,
    document_id: `doc-audit-${i + 1}`,
    reviewer_id: null,
    review_type: 'auto',
    status: 'pending',
    quality_score: 0.35 + (i * 0.1),
    content_length_ok: i > 0,
    duplicate_ratio: 0.05 * i,
    garble_ratio: 0.02 * i,
    blank_ratio: 0.1,
    overlap_score: 0.1,
    reviewer_comment: i === 0 ? 'Content too short' : 'Suspicious characters found',
    created_at: new Date(Date.now() - i * 3600000).toISOString(),
    updated_at: new Date(Date.now() - i * 3600000).toISOString(),
}));

// 8. Evaluation Mock Data — Comprehensive Multi-Model Arena
export const mockEvalSets = [
    { id: 'set-finance', kb_id: 'kb-demo-smart-finance', name: 'Q4 财务合规性评估测试集', description: '针对税务扣除、印花税等核心财务知识的专项测试。', created_at: new Date(Date.now() - 10 * 86400000).toISOString() },
    { id: 'set-hr', kb_id: 'kb-demo-hr-policy', name: 'HR 劳动法应答质量评估集', description: '覆盖试用期、年假、产假、加班、竞业限制等常见问题。', created_at: new Date(Date.now() - 8 * 86400000).toISOString() },
    { id: 'set-finance-adv', kb_id: 'kb-demo-smart-finance', name: '高级财务场景综合测试集', description: '综合测试跨境电商税率、企业年金等进阶财务场景。', created_at: new Date(Date.now() - 5 * 86400000).toISOString() },
];

const _financeQA = [
    { question: '研发费用的加计扣除比例是多少？', ground_truth: '根据2023年新规，符合条件的研发费用加计扣除比例已统一提高至100%。' },
    { question: '差旅补助是否需要缴纳个人所得税？', ground_truth: '合理的差旅补贴和误餐补助不属于工资薪金性质的补贴，不征收个人所得税。' },
    { question: '企业固定资产折旧的最低年限分别是多少？', ground_truth: '房屋建筑物20年，飞机火车轮船设备10年，器具工具5年，电子设备3年。' },
    { question: '小型微利企业所得税优惠政策是什么？', ground_truth: '减按25%计入应纳税所得额，按20%税率缴纳，实际税负率为5%。' },
    { question: '增值税留抵退税政策适用于哪些行业？', ground_truth: '2022年起扩大至所有行业，小微企业和制造业等6个行业可申请退还存量留抵税额。' },
    { question: '企业年金缴费的税前扣除标准是多少？', ground_truth: '企业缴费部分不超过职工工资总额5%标准内可税前扣除。' },
    { question: '跨境电商综合税率如何计算？', ground_truth: '关税×0%+增值税×70%+消费税×70%，单次限额5000元，年度限额26000元。' },
    { question: '合同印花税的税率是多少？', ground_truth: '买卖合同万分之三，借款合同万分之零点五，技术合同万分之三，财产租赁合同千分之一。' },
];

const _hrQA = [
    { question: '员工试用期最长可以设置多久？', ground_truth: '不满一年不超过1个月，1-3年不超过2个月，3年以上不超过6个月。' },
    { question: '公司解除劳动合同需要提前多少天通知？', ground_truth: '提前三十日以书面形式通知或额外支付一个月工资。' },
    { question: '年假天数如何计算？', ground_truth: '工龄满1-10年为5天，满10-20年为10天，满20年为15天。' },
    { question: '产假法定天数是多少？', ground_truth: '98天产假，难产增加15天，多胞胎每多一个增加15天。' },
    { question: '加班费的计算标准是什么？', ground_truth: '工作日150%，休息日200%，法定休假日300%。' },
    { question: '竞业限制补偿金不低于多少？', ground_truth: '不低于解除前12个月平均工资的30%，且不低于当地最低工资标准，期限不超过2年。' },
];

function _makeDetails(qa: typeof _financeQA, qualityLevel: 'high' | 'medium' | 'low') {
    const ranges = { high: [0.82, 0.98], medium: [0.60, 0.82], low: [0.45, 0.72] };
    const [lo, hi] = ranges[qualityLevel];
    return qa.map(item => {
        const f = +(lo + Math.random() * (hi - lo)).toFixed(2);
        const r = +(lo + Math.random() * (hi - lo)).toFixed(2);
        const cp = +((f * 0.9) + Math.random() * 0.1).toFixed(2);
        const cr = +((r * 0.85) + Math.random() * 0.12).toFixed(2);
        const goodAnswer = qualityLevel === 'high' ? item.ground_truth : qualityLevel === 'medium' ? item.ground_truth.slice(0, 40) + '...' : '这个要根据具体情况来判断，建议咨询专业人士。';
        return { question: item.question, ground_truth: item.ground_truth, answer: goodAnswer, faithfulness: f, relevance: r, context_precision: Math.min(cp, 1), context_recall: Math.min(cr, 1) };
    });
}

function _avg(arr: number[]) { return +(arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(4); }

function _makeReport(id: string, setId: string, kbId: string, model: string, qa: typeof _financeQA, quality: 'high' | 'medium' | 'low', latency: number, cost: number, tokens: number, daysAgo: number) {
    const details = _makeDetails(qa, quality);
    const faith = _avg(details.map(d => d.faithfulness));
    const relev = _avg(details.map(d => d.relevance));
    const prec = _avg(details.map(d => d.context_precision));
    const recall = _avg(details.map(d => d.context_recall));
    const total = +((faith + relev + prec + recall) / 4).toFixed(4);
    return {
        id, set_id: setId, kb_id: kbId, model_name: model,
        faithfulness: faith, answer_relevance: relev, context_precision: prec, context_recall: recall, total_score: total,
        latency_ms: latency, cost, token_usage: tokens,
        details_json: JSON.stringify(details),
        status: 'completed', created_at: new Date(Date.now() - daysAgo * 86400000).toISOString()
    };
}

export const mockReports = [
    // GPT-4 Turbo — High Quality, High Cost
    _makeReport('rep-gpt4-fin-1', 'set-finance', 'kb-demo-smart-finance', 'gpt-4-turbo', _financeQA, 'high', 2150, 0.0612, 2100, 7),
    _makeReport('rep-gpt4-hr-1', 'set-hr', 'kb-demo-hr-policy', 'gpt-4-turbo', _hrQA, 'high', 1980, 0.0534, 1850, 5),
    _makeReport('rep-gpt4-fin-2', 'set-finance', 'kb-demo-smart-finance', 'gpt-4-turbo', _financeQA, 'high', 2300, 0.0689, 2350, 2),

    // Claude 3 Opus — Highest Quality, Highest Cost
    _makeReport('rep-claude-fin-1', 'set-finance', 'kb-demo-smart-finance', 'claude-3-opus', _financeQA, 'high', 2800, 0.0823, 2600, 7),
    _makeReport('rep-claude-hr-1', 'set-hr', 'kb-demo-hr-policy', 'claude-3-opus', _hrQA, 'high', 3100, 0.0912, 2900, 5),
    _makeReport('rep-claude-fin-2', 'set-finance', 'kb-demo-smart-finance', 'claude-3-opus', _financeQA, 'high', 2650, 0.0756, 2400, 2),

    // DeepSeek Chat — Good Quality, Very Low Cost
    _makeReport('rep-ds-fin-1', 'set-finance', 'kb-demo-smart-finance', 'deepseek-chat', _financeQA, 'medium', 520, 0.0012, 1100, 7),
    _makeReport('rep-ds-hr-1', 'set-hr', 'kb-demo-hr-policy', 'deepseek-chat', _hrQA, 'medium', 480, 0.0009, 950, 5),
    _makeReport('rep-ds-fin-2', 'set-finance', 'kb-demo-smart-finance', 'deepseek-chat', _financeQA, 'medium', 560, 0.0015, 1250, 2),

    // GPT-3.5 Turbo — Medium Quality, Low Cost
    _makeReport('rep-gpt35-fin-1', 'set-finance', 'kb-demo-smart-finance', 'gpt-3.5-turbo', _financeQA, 'medium', 650, 0.0038, 1400, 7),
    _makeReport('rep-gpt35-hr-1', 'set-hr', 'kb-demo-hr-policy', 'gpt-3.5-turbo', _hrQA, 'medium', 580, 0.0029, 1200, 5),
    _makeReport('rep-gpt35-fin-2', 'set-finance', 'kb-demo-smart-finance', 'gpt-3.5-turbo', _financeQA, 'medium', 700, 0.0042, 1500, 2),

    // Llama-3-8B — Lower Quality, Cheapest
    _makeReport('rep-llama-fin-1', 'set-finance', 'kb-demo-smart-finance', 'llama-3-8b', _financeQA, 'low', 350, 0.0003, 800, 7),
    _makeReport('rep-llama-hr-1', 'set-hr', 'kb-demo-hr-policy', 'llama-3-8b', _hrQA, 'low', 280, 0.0002, 650, 5),
    _makeReport('rep-llama-fin-2', 'set-finance', 'kb-demo-smart-finance', 'llama-3-8b', _financeQA, 'low', 380, 0.0004, 900, 2),
];

// 8b. Bad Cases Mock Data
export const mockBadCases = [
    { id: 'bc-1', question: '研发费用加计扣除的比例是多少？', bad_answer: '一般企业的研发费用可以按照50%进行加计扣除。', expected_answer: '100%加计扣除', reason: '数据过时 — 引用了2018年前的旧政策', status: 'reviewed', created_at: new Date(Date.now() - 6 * 86400000).toISOString() },
    { id: 'bc-2', question: '小微企业所得税税率是多少？', bad_answer: '小微企业按照25%的标准税率缴纳企业所得税。', expected_answer: '实际税负率5%', reason: '幻觉回答 — 混淆了标准税率和优惠税率', status: 'pending', created_at: new Date(Date.now() - 5 * 86400000).toISOString() },
    { id: 'bc-3', question: '员工试用期最长能设置多久？', bad_answer: '试用期一般为3个月。', expected_answer: '根据合同期限分类：1/2/6个月', reason: '回答不完整 — 缺少按合同期限分段说明', status: 'pending', created_at: new Date(Date.now() - 4 * 86400000).toISOString() },
    { id: 'bc-4', question: '加班费怎么算？', bad_answer: '加班费按基本工资的两倍计算。', expected_answer: '工作日150%，休息日200%，法定节假日300%', reason: '事实性错误 — 统一按200%计算是错误的', status: 'fixed', created_at: new Date(Date.now() - 3 * 86400000).toISOString() },
    { id: 'bc-5', question: '跨境电商进口怎么交税？', bad_answer: '跨境电商进口需要全额缴纳关税和增值税。', expected_answer: '关税0%，增值税消费税按70%征收', reason: '严重失实 — 忽略了跨境电商专属优惠政策', status: 'added_to_dataset', created_at: new Date(Date.now() - 2 * 86400000).toISOString() },
    { id: 'bc-6', question: '竞业限制的补偿金标准是什么？', bad_answer: '竞业限制没有强制的补偿金标准。', expected_answer: '不低于前12个月平均工资30%', reason: '法律知识错误 — 最高院司法解释已有明确规定', status: 'reviewed', created_at: new Date(Date.now() - 1 * 86400000).toISOString() },
    { id: 'bc-7', question: '年假怎么算？在公司工作了8年有几天？', bad_answer: '年假统一为10天。', expected_answer: '需区分累计工龄，1-10年为5天', reason: '回答含糊且错误 — 没有区分累计工龄和本单位工龄', status: 'pending', created_at: new Date(Date.now() - 18 * 3600000).toISOString() },
    { id: 'bc-8', question: '合同印花税是多少？', bad_answer: '印花税税率为万分之五。', expected_answer: '按合同类型分：买卖万分之三等', reason: '笼统回答 — 2022年新印花税法区分了多种合同类型', status: 'pending', created_at: new Date(Date.now() - 6 * 3600000).toISOString() },
];

// 9. Knowledge Graph Mock Data (for GraphVisualizer)
export const mockGraphData = {
    nodes: [
        { id: 'HiveMind', name: 'HiveMind', label: 'System', val: 18, color: '#06D6A0' },
        { id: 'RAGPipeline', name: 'RAG Pipeline', label: 'Component', val: 14, color: '#118AB2' },
        { id: 'AgentSwarm', name: 'Agent Swarm', label: 'Component', val: 14, color: '#118AB2' },
        { id: 'Neo4j', name: 'Neo4j', label: 'Technology', val: 10, color: '#FFD166' },
        { id: 'Elasticsearch', name: 'Elasticsearch', label: 'Technology', val: 10, color: '#FFD166' },
        { id: 'LangGraph', name: 'LangGraph', label: 'Framework', val: 10, color: '#EF476F' },
        { id: 'VectorStore', name: 'Vector Store', label: 'Component', val: 12, color: '#118AB2' },
        { id: 'GraphRAG', name: 'GraphRAG', label: 'Component', val: 12, color: '#118AB2' },
        { id: 'BatchEngine', name: 'Batch Engine', label: 'Component', val: 12, color: '#118AB2' },
        { id: 'Reranker', name: 'Cross-Encoder Reranker', label: 'Component', val: 8, color: '#94A3B8' },
        { id: 'Chunking', name: 'Parent-Child Chunking', label: 'Strategy', val: 8, color: '#94A3B8' },
        { id: 'HyDE', name: 'HyDE Query Expansion', label: 'Strategy', val: 8, color: '#94A3B8' },
        { id: 'Supervisor', name: 'Supervisor Agent', label: 'Agent', val: 10, color: '#06D6A0' },
        { id: 'CriticAgent', name: 'Critic Agent', label: 'Agent', val: 8, color: '#06D6A0' },
        { id: 'MinerU', name: 'MinerU Parser', label: 'Plugin', val: 6, color: '#94A3B8' },
    ],
    links: [
        { source: 'HiveMind', target: 'RAGPipeline', type: 'CONTAINS' },
        { source: 'HiveMind', target: 'AgentSwarm', type: 'CONTAINS' },
        { source: 'HiveMind', target: 'BatchEngine', type: 'CONTAINS' },
        { source: 'RAGPipeline', target: 'VectorStore', type: 'USES' },
        { source: 'RAGPipeline', target: 'GraphRAG', type: 'USES' },
        { source: 'RAGPipeline', target: 'Reranker', type: 'USES' },
        { source: 'RAGPipeline', target: 'Chunking', type: 'USES' },
        { source: 'RAGPipeline', target: 'HyDE', type: 'USES' },
        { source: 'VectorStore', target: 'Elasticsearch', type: 'POWERED_BY' },
        { source: 'GraphRAG', target: 'Neo4j', type: 'POWERED_BY' },
        { source: 'AgentSwarm', target: 'LangGraph', type: 'POWERED_BY' },
        { source: 'AgentSwarm', target: 'Supervisor', type: 'CONTAINS' },
        { source: 'AgentSwarm', target: 'CriticAgent', type: 'CONTAINS' },
        { source: 'BatchEngine', target: 'LangGraph', type: 'POWERED_BY' },
        { source: 'RAGPipeline', target: 'MinerU', type: 'USES' },
    ]
};

// 10. Batch Jobs Mock Data
export const mockBatchJobs = [
    {
        id: 'job-001',
        name: '文档摄入 Pipeline',
        description: '批量解析 + 向量化 + 知识图谱抽取',
        status: 'running',
        max_concurrency: 3,
        timeout_per_task: 300,
        on_failure: 'continue',
        created_at: new Date(Date.now() - 600000).toISOString(),
        started_at: new Date(Date.now() - 500000).toISOString(),
        total_tasks: 4,
        progress: { success: 1, running: 2, pending: 1 },
        completion_rate: 0.25,
        success_rate: 0.25,
        tasks: {
            'task-001': { id: 'task-001', batch_job_id: 'job-001', name: '文档解析 (batch-1)', status: 'success', priority: 3, depends_on: [], steps: [], input_data: {}, output_data: { parsed_pages: 42 }, error_message: '', worker_id: 'w-1', is_terminal: false, created_at: new Date(Date.now() - 300000).toISOString(), started_at: new Date(Date.now() - 300000).toISOString(), completed_at: new Date(Date.now() - 60000).toISOString(), duration_seconds: 240 },
            'task-002': { id: 'task-002', batch_job_id: 'job-001', name: '向量索引生成', status: 'running', priority: 3, depends_on: ['task-001'], steps: [], input_data: {}, output_data: {}, error_message: '', worker_id: 'w-2', is_terminal: false, created_at: new Date(Date.now() - 300000).toISOString(), started_at: new Date(Date.now() - 50000).toISOString(), duration_seconds: 50 },
            'task-003': { id: 'task-003', batch_job_id: 'job-001', name: '知识图谱抽取', status: 'running', priority: 2, depends_on: ['task-001'], steps: [], input_data: {}, output_data: {}, error_message: '', worker_id: 'w-3', is_terminal: false, created_at: new Date(Date.now() - 300000).toISOString(), started_at: new Date(Date.now() - 40000).toISOString(), duration_seconds: 40 },
            'task-004': { id: 'task-004', batch_job_id: 'job-001', name: '数据脱敏审核', status: 'pending', priority: 1, depends_on: ['task-002', 'task-003'], steps: [], input_data: {}, output_data: {}, error_message: '', worker_id: '', is_terminal: true, created_at: new Date(Date.now() - 300000).toISOString() },
        }
    },
    {
        id: 'job-002',
        name: '全库重索引',
        description: '重建所有知识库的向量索引并生成质量报告',
        status: 'completed',
        max_concurrency: 2,
        timeout_per_task: 600,
        on_failure: 'abort',
        created_at: new Date(Date.now() - 7200000).toISOString(),
        started_at: new Date(Date.now() - 7000000).toISOString(),
        completed_at: new Date(Date.now() - 1800000).toISOString(),
        total_tasks: 2,
        progress: { success: 2 },
        completion_rate: 1.0,
        success_rate: 1.0,
        tasks: {
            'task-005': { id: 'task-005', batch_job_id: 'job-002', name: '全库重索引', status: 'success', priority: 4, depends_on: [], steps: [], input_data: {}, output_data: { reindexed: 128 }, error_message: '', worker_id: 'w-1', is_terminal: false, created_at: new Date(Date.now() - 7200000).toISOString(), started_at: new Date(Date.now() - 7200000).toISOString(), completed_at: new Date(Date.now() - 3600000).toISOString(), duration_seconds: 3600 },
            'task-006': { id: 'task-006', batch_job_id: 'job-002', name: '质量评估报告', status: 'success', priority: 3, depends_on: ['task-005'], steps: [], input_data: {}, output_data: { score: 0.91 }, error_message: '', worker_id: 'w-2', is_terminal: true, created_at: new Date(Date.now() - 7200000).toISOString(), started_at: new Date(Date.now() - 3500000).toISOString(), completed_at: new Date(Date.now() - 1800000).toISOString(), duration_seconds: 1700 },
        }
    }
];

// 11. Agent Traces Mock Data (DAG)
export const mockTraces = {
    nodes: [
        { id: '1', label: '意图解析 (Supervisor)', agent: 'Supervisor', status: 'completed' },
        { id: '2', label: '向量搜索 (RAG专家)', agent: 'RAG-Specialist', status: 'completed' },
        { id: '3', label: '图谱检索 (RAG专家)', agent: 'RAG-Specialist', status: 'completed' },
        { id: '4', label: '答案生成 (架构师)', agent: 'Code-Architect', status: 'running' },
        { id: '5', label: '质量审查 (审查员)', agent: 'Critic-Agent', status: 'pending' },
    ],
    links: [
        { source: '1', target: '2' },
        { source: '1', target: '3' },
        { source: '2', target: '4' },
        { source: '3', target: '4' },
        { source: '4', target: '5' },
    ]
};
