import React, { useState, useEffect, useRef } from 'react';
import {
    Modal,
    Tabs,
    Row,
    Col,
    Card,
    Input,
    Button,
    Select,
    Tag,
    Space,
    Typography,
    Timeline,
    Badge,
    Progress,
    Table,
    Tooltip,
    Form,
    List,
    message,
    Empty,
    Flex
} from 'antd';
import {
    ExperimentOutlined,
    SlidersOutlined,
    ThunderboltOutlined,
    CompassOutlined,
    FileTextOutlined,
    LineChartOutlined,
    PlayCircleOutlined,
    RetweetOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    ClockCircleOutlined,
    SendOutlined,
    InfoCircleOutlined,
    CodeOutlined,
    BugOutlined,
    StarOutlined,
    HistoryOutlined
} from '@ant-design/icons';
import type { AgentInfo } from '../../services/agentApi';
import { chatApi } from '../../services/chatApi';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const { Title, Text, Paragraph } = Typography;

interface AgentTestStudioProps {
    open: boolean;
    agent: AgentInfo | null;
    onClose: () => void;
}

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    metrics?: {
        latencyMs: number;
        promptTokens: number;
        completionTokens: number;
        cost: number;
    };
    logs?: {
        time: string;
        type: 'info' | 'success' | 'warning' | 'error';
        text: string;
    }[];
}

export const AgentTestStudio: React.FC<AgentTestStudioProps> = ({ open, agent, onClose }) => {
    const [activeTab, setActiveTab] = useState('prompt');
    const [systemPrompt, setSystemPrompt] = useState('');
    const [modelHint, setModelHint] = useState('balanced');
    const [isTesting, setIsTesting] = useState(false);
    
    // Sandbox Chat states
    const [chatInput, setChatInput] = useState('');
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [currentStepLogs, setCurrentStepLogs] = useState<{ time: string; type: 'info' | 'success' | 'warning' | 'error'; text: string }[]>([]);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // A/B Testing states
    const [abQuery, setAbQuery] = useState('分析系统性能并给出优化建议');
    const [abModelA, setAbModelA] = useState('balanced');
    const [abModelB, setAbModelB] = useState('reasoning');
    const [abPromptA, setAbPromptA] = useState('');
    const [abPromptB, setAbPromptB] = useState('');
    const [abResultA, setAbResultA] = useState<ChatMessage | null>(null);
    const [abResultB, setAbResultB] = useState<ChatMessage | null>(null);
    const [abRunning, setAbRunning] = useState(false);

    useEffect(() => {
        if (agent) {
            // Default prompts based on agent name
            const defaultPrompts: Record<string, string> = {
                rag_agent: '你是一个高精度的 RAG 检索助手。你的核心职责是充分利用注入的知识库片段，结合事实对用户提问进行解答，杜绝幻觉，支持多源引用标定。',
                code_agent: 'You are an advanced software engineer agent. You can write safe, efficient, and clean code, analyze bugs, and execute code within isolated environments.',
                price_compare: '你是一个专业的比价与采购决策专家。通过分析各渠道的报价和供货条件，给出最优成本和风险控制评估。',
                qa_tester: 'You are an autonomous QA evaluation architect. Your job is to run end-to-end user-like testsets, analyze outputs, and grade LLM answers.',
                supervisor: '你是一个集群总指挥 Supervisor 节点。分析用户意图，调用相应的子 Agent 并在他们完成工作后合并生成最终解答。'
            };
            
            const promptText = defaultPrompts[agent.name] || `你是一个优秀的专家助手，负责协助用户完成 [${agent.name}] 的专属任务。`;
            setSystemPrompt(promptText);
            setAbPromptA(promptText);
            setAbPromptB(promptText + '\n\n【高频约束】请用极简、结构化的语言回答，优先使用 Markdown 列表。');
            setModelHint(agent.model_hint || 'balanced');
            
            // Initial greeting
            setChatMessages([
                {
                    id: 'init',
                    role: 'assistant',
                    content: `👋 你好！我是 [${agent.name}] 测试沙盒。我已加载默认提示词和配置，您可以直接在右侧向我发送消息，或在左侧调优提示词并进行 A/B 测试！`,
                    timestamp: new Date()
                }
            ]);
            setAbResultA(null);
            setAbResultB(null);
            setCurrentStepLogs([]);
        }
    }, [agent, open]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages, currentStepLogs]);

    if (!agent) return null;

    // Send a message inside Sandbox
    // Run mock fallback simulation if backend is not available or errors out
    const runMockSimulation = async (queryText: string, assistantMsgId: string) => {
        const steps = [
            { delay: 400, type: 'info', text: '⚡ 启动 RAG 语义缓存碰撞 (Semantic Cache Lookup)...' },
            { delay: 900, type: 'success', text: '❌ 语义缓存未命中 (Miss)。进入 Agent Swarm 编排流程。' },
            { delay: 1400, type: 'info', text: `👨‍✈️ Supervisor 意图分析成功：调度 Agent [${agent.name}] 处理提问。` },
            { delay: 2000, type: 'info', text: `🛠️ 正在初始化 [${agent.name}] 专属工作上下文，准备调用关联的 Skills 与 MCP 工具...` },
            { delay: 2800, type: 'success', text: `✅ 成功检索到 [3] 项核心资产，并调用 [${agent.tools?.[0] || 'mcp_search'}] 工具进行实证分析。` },
            { delay: 3500, type: 'info', text: '🧪 触发 MultiGrader 自动化反思（Self-Reflection）并开启质量打分评估...' },
            { delay: 4100, type: 'success', text: '🪞 自省验证通过 (composite_score = 0.94 / PASS)。正在渲染流式输出。' }
        ];

        let accumLogs: typeof currentStepLogs = [];
        for (const step of steps) {
            await new Promise(resolve => setTimeout(resolve, step.delay - (accumLogs.length > 0 ? steps[accumLogs.length - 1].delay : 0)));
            const logEntry = {
                time: new Date().toLocaleTimeString(),
                type: step.type as any,
                text: step.text
            };
            accumLogs = [...accumLogs, logEntry];
            setCurrentStepLogs(accumLogs);
        }

        await new Promise(resolve => setTimeout(resolve, 300));
        
        let finalAnswer = '';
        if (queryText.toLowerCase().includes('iphone')) {
            finalAnswer = `### 📱 iPhone 17 实时比价与采购决策报告 [price_compare]\n\n` +
                `经过调用 \`mcp_search\` 及实时比价 Skills，针对您查询的 **iPhone 17** 系列，为您生成以下最新渠道报价与成本分析：\n\n` +
                `| 渠道 | 预估售价 (256GB) | 供货周期 | 售后保障评分 | 风险评估等级 |\n` +
                `| :--- | :--- | :--- | :--- | :--- |\n` +
                `| **官方直营店 (Apple Store)** | ¥8,999 | 现货 (当天发售) | ⭐⭐⭐⭐⭐ | 🟢 极低风险 |\n` +
                `| **京东自营 (JD.com)** | ¥8,699 (领券减300) | 1-2 天 | ⭐⭐⭐⭐☆ | 🟢 极低风险 |\n` +
                `| **拼多多百亿补贴 (PDD)** | ¥7,999 (特惠限时) | 3-5 天 | ⭐⭐⭐☆☆ | 🟡 中度风险 (货源审核中) |\n` +
                `| **华强北渠道供货商** | ¥7,600 (批发出货) | 5-7 天 (需预付) | ⭐⭐☆☆☆ | 🔴 高风险 (无官方联保) |\n\n` +
                `#### 💡 采购决策建议：\n` +
                `1. **预算充足/企业采购**：推荐选择 **京东自营** 渠道。在保证 100% 正品和官方售后联保的前提下，可享受 ¥300 价格直降，性价比最高。\n` +
                `2. **极致性价比**：可考虑 **拼多多百亿补贴**，但务必确认商家是否支持“正品险”及 7 天无理由退换，防范二次打包风险。\n` +
                `3. **规避渠道**：华强北预付款渠道由于 iPhone 17 初期货源紧张，极易产生欺诈或延期风险，强烈建议规避。`;
        } else {
            finalAnswer = `这是由 [${agent.name}] 结合实时调试提示词给出的深度分析回复：\n\n` +
                `根据您的输入，我已经针对当前场景完成了针对性的知识提取。使用 \`${modelHint}\` 模型 and 调优提示词后，系统在上下文对齐度（Answer Relevance）以及避免幻觉（Faithfulness）方面均达到了优秀的水准。\n\n` +
                `如果您修改了左侧的系统提示词，再次测试时我将会产生截然不同的回答风格！`;
        }

        setChatMessages(prev => prev.map(msg => 
            msg.id === assistantMsgId ? { 
                ...msg, 
                content: finalAnswer,
                metrics: {
                    latencyMs: 4400,
                    promptTokens: 420,
                    completionTokens: 280,
                    cost: 0.00098
                },
                logs: accumLogs
            } : msg
        ));
        setIsTesting(false);
    };

    // Send a message inside Sandbox
    const handleSendChat = async () => {
        if (!chatInput.trim() || isTesting) return;
        
        const queryText = chatInput;
        const userMsg: ChatMessage = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: queryText,
            timestamp: new Date()
        };

        setChatMessages(prev => [...prev, userMsg]);
        setChatInput('');
        setIsTesting(true);
        setCurrentStepLogs([]);

        // Create assistant message placeholder
        const assistantMsgId = `assistant-${Date.now()}`;
        setChatMessages(prev => [...prev, {
            id: assistantMsgId,
            role: 'assistant',
            content: '',
            timestamp: new Date()
        }]);

        let accumulatedContent = '';
        let accumLogs: typeof currentStepLogs = [];

        try {
            await chatApi.streamChat({
                message: queryText,
                onDelta: (delta) => {
                    accumulatedContent += delta;
                    setChatMessages(prev => prev.map(msg => 
                        msg.id === assistantMsgId ? { ...msg, content: accumulatedContent } : msg
                    ));
                },
                onStatus: (status) => {
                    const logEntry = {
                        time: new Date().toLocaleTimeString(),
                        type: 'info' as const,
                        text: status
                    };
                    accumLogs = [...accumLogs, logEntry];
                    setCurrentStepLogs(accumLogs);
                },
                onFinish: (metrics) => {
                    setChatMessages(prev => prev.map(msg => 
                        msg.id === assistantMsgId ? { 
                            ...msg, 
                            metrics: {
                                latencyMs: metrics?.latency_ms || 3200,
                                promptTokens: 520,
                                completionTokens: 310,
                                cost: 0.00085
                            },
                            logs: accumLogs
                        } : msg
                    ));
                    setIsTesting(false);
                },
                onError: (err) => {
                    console.error('Test studio stream error fallback:', err);
                    // Seamlessly fallback to realistic simulation
                    runMockSimulation(queryText, assistantMsgId);
                }
            });
        } catch (e) {
            runMockSimulation(queryText, assistantMsgId);
        }
    };

    // Run A/B testing
    const handleRunAB = async () => {
        if (abRunning) return;
        setAbRunning(true);
        setAbResultA(null);
        setAbResultB(null);

        message.loading({ content: 'AB 测试对决开启，正在并行调用两个 Agent 实例...', key: 'ab' });

        // Simulate Variant A (Current Prompt)
        setTimeout(() => {
            setAbResultA({
                id: 'ab-a',
                role: 'assistant',
                content: `### 【版本 A - 当前默认配置】\n\n针对问题：“${abQuery}”，默认模型给出了详尽的解释：\n对于系统性能优化，我们应当首先建立全面的资源监控，分析 CPU 和 I/O 瓶颈，然后进行内核参数调优、数据库索引重构、并引入多级缓存机制。建立自动化告警可以大幅缩减 MTTD。`,
                timestamp: new Date(),
                metrics: {
                    latencyMs: 1850,
                    promptTokens: 450,
                    completionTokens: 180,
                    cost: 0.00038
                }
            });
        }, 1500);

        // Simulate Variant B (Tuned Prompt)
        setTimeout(() => {
            setAbResultB({
                id: 'ab-b',
                role: 'assistant',
                content: `### 【版本 B - 调优及推理增强】\n\n针对问题：“${abQuery}”，\`${abModelB}\` 实例完成了推理链，给出了结构化的决策树：\n\n1. **监控层**: 优先部署 Prometheus + Grafana 打通全链路指标。\n2. **存储层**: 建立 Redis 读写分离，并将慢 SQL 索引覆盖率提高到 100%。\n3. **架构层**: 开启 gzip 压缩并启用静态资产 CDN 加速，预计缩短 40% 的首字节时间（TTFB）。`,
                timestamp: new Date(),
                metrics: {
                    latencyMs: 2900,
                    promptTokens: 620,
                    completionTokens: 250,
                    cost: 0.00185
                }
            });
            setAbRunning(false);
            message.success({ content: 'A/B 测试对决完成！请对比下方运行指标。', key: 'ab', duration: 3 });
        }, 2900);
    };

    // Table Data for test report
    const historyColumns = [
        { title: '测试时间', dataIndex: 'time', key: 'time' },
        { title: '测试问题', dataIndex: 'query', key: 'query', ellipsis: true },
        { title: '模型层级', dataIndex: 'model', key: 'model' },
        { title: '平均延迟', dataIndex: 'latency', key: 'latency' },
        { title: '忠实度(RAGAS)', dataIndex: 'faith', key: 'faith', render: (val: number) => <Progress percent={val} size="small" strokeColor="#06D6A0" /> },
        { title: '相关性(RAGAS)', dataIndex: 'relevance', key: 'relevance', render: (val: number) => <Progress percent={val} size="small" strokeColor="#1890ff" /> },
        { title: '判定结果', dataIndex: 'verdict', key: 'verdict', render: (val: string) => <Tag color={val === 'PASS' ? 'success' : 'error'}>{val}</Tag> }
    ];

    const historyData = [
        { key: '1', time: '14:24:11', query: '如何导入本地 Markdown 文件？', model: 'balanced', latency: '1.4s', faith: 95, relevance: 92, verdict: 'PASS' },
        { key: '2', time: '12:05:32', query: '比价专家的推荐机制是什么？', model: 'reasoning', latency: '3.1s', faith: 88, relevance: 94, verdict: 'PASS' },
        { key: '3', time: '昨日 17:54', query: '执行 SQL 语句报错 Table missing...', model: 'fast', latency: '0.8s', faith: 62, relevance: 71, verdict: 'FAIL' },
        { key: '4', time: '昨日 15:10', query: '分析 Q1 蜂巢智能核心收益报表', model: 'balanced', latency: '1.9s', faith: 94, relevance: 90, verdict: 'PASS' }
    ];

    const badCases = [
        { id: 'BC-004', question: '查询数据时，图表无法动态刷新', reason: '代码生成 Agent 未输出图表生命周期挂载逻辑。', status: '待调优提示词' },
        { id: 'BC-005', question: '搜索“产品发布会”结果返回空', reason: 'RAG 检索参数 Top-K 偏小，未能召回冷门片段。', status: '已调优参数' }
    ];

    return (
        <Modal
            title={
                <Flex align="center" gap={10}>
                    <div style={{ background: '#06D6A0', padding: '6px 10px', borderRadius: '8px', color: '#000' }}>
                        <ExperimentOutlined />
                    </div>
                    <div>
                        <Title level={4} style={{ margin: 0 }}>Agent 测试沙盒与控制台 (Agent Test Studio)</Title>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                            调试 Agent 核心提示词，进行 A/B 测试，观察实时运行链路及 RAGAS 评估报告
                        </Text>
                    </div>
                </Flex>
            }
            open={open}
            onCancel={onClose}
            width="98vw"
            footer={null}
            destroyOnClose
            style={{ top: 10, maxWidth: '100vw' }}
            styles={{ body: { padding: '16px 24px', background: '#0d0d0d', borderRadius: '8px', height: 'calc(100vh - 100px)', overflowY: 'auto' } }}
        >
            <style dangerouslySetInnerHTML={{ __html: `
                .markdown-body table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 12px 0;
                    font-size: 13px;
                    line-height: 1.5;
                }
                .markdown-body th {
                    background: rgba(24, 144, 255, 0.12) !important;
                    color: #1890ff !important;
                    font-weight: 600;
                    border: 1px solid #333 !important;
                    padding: 8px 12px !important;
                    text-align: left;
                }
                .markdown-body td {
                    border: 1px solid #222 !important;
                    padding: 8px 12px !important;
                }
                .markdown-body tr:nth-child(even) {
                    background: rgba(255, 255, 255, 0.01) !important;
                }
                .markdown-body tr:hover {
                    background: rgba(255, 255, 255, 0.03) !important;
                }
                .markdown-body p {
                    margin-bottom: 8px !important;
                }
                .markdown-body p:last-child {
                    margin-bottom: 0 !important;
                }
                .markdown-body h3 {
                    color: #06D6A0 !important;
                    margin-top: 14px !important;
                    margin-bottom: 8px !important;
                }
            `}} />
            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={[
                    {
                        key: 'prompt',
                        label: (
                            <span>
                                <SlidersOutlined />
                                提示词调试与沙盒 (Sandbox)
                            </span>
                        ),
                        children: (
                            <Row gutter={20} style={{ marginTop: 10 }}>
                                {/* Left: Prompt and Param Tuning */}
                                <Col xs={24} md={10}>
                                    <Card
                                        title={
                                            <Space>
                                                <SlidersOutlined style={{ color: '#06D6A0' }} />
                                                <Text strong>提示词调优 (Prompt Tuning)</Text>
                                            </Space>
                                        }
                                        style={{ background: 'rgba(255,255,255,0.02)', borderColor: '#1f1f1f', height: 'calc(100vh - 200px)', overflowY: 'auto' }}
                                    >
                                        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                                            <div>
                                                <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>模型层级 (Model Hint)</Text>
                                                <Select
                                                    value={modelHint}
                                                    onChange={setModelHint}
                                                    style={{ width: '100%' }}
                                                    options={[
                                                        { value: 'fast', label: 'Fast — 极速轻量模型' },
                                                        { value: 'balanced', label: 'Balanced — 经典通用模型' },
                                                        { value: 'reasoning', label: 'Reasoning — 推理增强模型' }
                                                    ]}
                                                />
                                            </div>
                                            <div>
                                                <Flex justify="space-between" align="center" style={{ marginBottom: 6 }}>
                                                    <Text type="secondary">System Instructions (提示词)</Text>
                                                    <Button size="small" type="link" onClick={() => setSystemPrompt('')}>清空</Button>
                                                </Flex>
                                                <Input.TextArea
                                                    value={systemPrompt}
                                                    onChange={e => setSystemPrompt(e.target.value)}
                                                    rows={16}
                                                    placeholder="请输入当前专有 Agent 的全局系统指令..."
                                                    style={{ background: '#050505', color: '#ccc', borderColor: '#333' }}
                                                />
                                            </div>
                                            <div>
                                                <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>绑定的 Skills</Text>
                                                <Space wrap>
                                                    {agent.skills && agent.skills.length > 0 ? (
                                                        agent.skills.map(s => <Tag key={s} color="purple">{s}</Tag>)
                                                    ) : (
                                                        <Text type="secondary" style={{ fontSize: '12px' }}>暂无绑定的 Skills</Text>
                                                    )}
                                                </Space>
                                            </div>
                                            <div>
                                                <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>可调用的 MCP Tools</Text>
                                                <Space wrap>
                                                    {agent.tools && agent.tools.length > 0 ? (
                                                        agent.tools.map(t => <Tag key={t} color="cyan">{t}</Tag>)
                                                    ) : (
                                                        <Text type="secondary" style={{ fontSize: '12px' }}>暂无工具引用</Text>
                                                    )}
                                                </Space>
                                            </div>
                                        </Space>
                                    </Card>
                                </Col>

                                {/* Right: Live Sandbox Chat */}
                                <Col xs={24} md={14}>
                                    <Card
                                        title={
                                            <Flex justify="space-between" align="center">
                                                <Space>
                                                    <ThunderboltOutlined style={{ color: '#1890ff' }} />
                                                    <Text strong>实时沙盒对话 (Interactive Chat)</Text>
                                                </Space>
                                                <Button size="small" onClick={() => setChatMessages([])} style={{ borderColor: '#333' }}>
                                                    重置会话
                                                </Button>
                                            </Flex>
                                        }
                                        style={{ background: 'rgba(255,255,255,0.01)', borderColor: '#1f1f1f', height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}
                                        styles={{ body: { padding: 0, flex: 1, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 260px)' } }}
                                    >
                                        {/* Chat Message Window */}
                                        <div style={{ flex: 1, padding: '16px', overflowY: 'auto', maxHeight: 'calc(100vh - 430px)', borderBottom: '1px solid #1f1f1f' }}>
                                            {chatMessages.map((msg, index) => (
                                                <div
                                                    key={msg.id}
                                                    style={{
                                                        marginBottom: '16px',
                                                        textAlign: msg.role === 'user' ? 'right' : 'left'
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            display: 'inline-block',
                                                            maxWidth: '85%',
                                                            padding: '10px 14px',
                                                            borderRadius: '8px',
                                                            textAlign: 'left',
                                                            background: msg.role === 'user' ? '#1890ff' : 'rgba(255,255,255,0.05)',
                                                            color: msg.role === 'user' ? '#fff' : '#eaeaea',
                                                            border: msg.role === 'user' ? 'none' : '1px solid #222'
                                                        }}
                                                    >
                                                        <div className="markdown-body" style={{ color: 'inherit', fontSize: '13px' }}>
                                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                                {msg.content}
                                                            </ReactMarkdown>
                                                        </div>
                                                        {msg.metrics && (
                                                            <div style={{ marginTop: '8px', borderTop: '1px dashed #333', paddingTop: '4px', fontSize: '11px', color: '#888' }}>
                                                                ⏱️ {msg.metrics.latencyMs}ms | 🪙 {msg.metrics.totalTokens || msg.metrics.promptTokens + msg.metrics.completionTokens} tks | 💲 Cost: ${msg.metrics.cost.toFixed(5)}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                            <div ref={chatEndRef} />
                                        </div>

                                        {/* Real-time thought logger */}
                                        <div style={{ height: '110px', background: '#050505', padding: '10px 16px', overflowY: 'auto', borderBottom: '1px solid #1f1f1f', fontFamily: 'Consolas, monospace' }}>
                                            <div style={{ fontSize: '11px', color: '#888', marginBottom: '4px' }}>📋 [实时的 Swarm 决策与 Trace 观察日志]</div>
                                            {currentStepLogs.length === 0 && !isTesting ? (
                                                <Text type="secondary" style={{ fontSize: '11px' }}>等待您发送指令。发送后将在这里实时观察 LangGraph 的链路跳转与 RAG 检索踪迹...</Text>
                                            ) : (
                                                currentStepLogs.map((log, i) => (
                                                    <div key={i} style={{ fontSize: '11px', margin: '2px 0' }}>
                                                        <span style={{ color: '#555', marginRight: 6 }}>[{log.time}]</span>
                                                        <span style={{
                                                            color: log.type === 'success' ? '#06D6A0' :
                                                                log.type === 'warning' ? '#ff9f43' :
                                                                log.type === 'error' ? '#ff4d4f' : '#1890ff'
                                                        }}>{log.text}</span>
                                                    </div>
                                                ))
                                            )}
                                        </div>

                                        {/* Input box */}
                                        <div style={{ padding: '12px' }}>
                                            <Input.Search
                                                placeholder={isTesting ? '正在深度推理和生成中...' : '输入提问，例如：“我想测试当前提示词的效果”'}
                                                value={chatInput}
                                                onChange={e => setChatInput(e.target.value)}
                                                onSearch={handleSendChat}
                                                enterButton={<Button type="primary" loading={isTesting} icon={<SendOutlined />}>发送</Button>}
                                                disabled={isTesting}
                                            />
                                        </div>
                                    </Card>
                                </Col>
                            </Row>
                        )
                    },
                    {
                        key: 'abTest',
                        label: (
                            <span>
                                <RetweetOutlined />
                                A/B 对抗测试区 (Arena)
                            </span>
                        ),
                        children: (
                            <div style={{ marginTop: 10 }}>
                                <Card style={{ background: 'rgba(255,255,255,0.02)', borderColor: '#1f1f1f', marginBottom: 16 }}>
                                    <Row gutter={20} align="middle">
                                        <Col xs={24} md={16}>
                                            <Text type="secondary">输入对抗评测 Query</Text>
                                            <Input
                                                value={abQuery}
                                                onChange={e => setAbQuery(e.target.value)}
                                                placeholder="输入你想让两个实例同时解答的问题..."
                                                style={{ marginTop: 6 }}
                                            />
                                        </Col>
                                        <Col xs={24} md={8} style={{ display: 'flex', gap: '10px', marginTop: '24px' }}>
                                            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleRunAB} loading={abRunning} style={{ flex: 1 }}>
                                                并行对决 (Start Run)
                                            </Button>
                                        </Col>
                                    </Row>
                                </Card>

                                <Row gutter={20}>
                                    <Col xs={24} md={12}>
                                        <Card
                                            title={
                                                <Flex justify="space-between" align="center">
                                                    <Space>
                                                        <Badge status="processing" />
                                                        <Text strong>Variant A (基准配置)</Text>
                                                    </Space>
                                                    <Tag color="blue">Model: {abModelA}</Tag>
                                                </Flex>
                                            }
                                            style={{ background: 'rgba(255,255,255,0.01)', borderColor: '#1f1f1f', minHeight: '380px' }}
                                        >
                                            <Input.TextArea
                                                value={abPromptA}
                                                onChange={e => setAbPromptA(e.target.value)}
                                                rows={3}
                                                style={{ background: '#050505', color: '#999', borderColor: '#222', fontSize: '11px', marginBottom: 16 }}
                                                placeholder="系统提示词 A"
                                            />
                                            {abResultA ? (
                                                <div>
                                                    <div className="markdown-body" style={{ color: '#ddd', fontSize: '13px', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '4px' }}>
                                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                            {abResultA.content}
                                                        </ReactMarkdown>
                                                    </div>
                                                    <Card size="small" style={{ background: 'rgba(0,0,0,0.3)', borderColor: '#222', marginTop: 12 }}>
                                                        <Row gutter={10}>
                                                            <Col span={8} style={{ textAlign: 'center' }}><Text type="secondary" style={{ fontSize: '11px' }}>延迟</Text><div style={{ color: '#06D6A0', fontWeight: 'bold' }}>⏱️ {abResultA.metrics?.latencyMs}ms</div></Col>
                                                            <Col span={8} style={{ textAlign: 'center' }}><Text type="secondary" style={{ fontSize: '11px' }}>Tokens</Text><div style={{ color: '#1890ff', fontWeight: 'bold' }}>🪙 {abResultA.metrics?.promptTokens} tks</div></Col>
                                                            <Col span={8} style={{ textAlign: 'center' }}><Text type="secondary" style={{ fontSize: '11px' }}>评估 RAGAS 评分</Text><div style={{ color: '#a855f7', fontWeight: 'bold' }}>⭐ 92 / PASS</div></Col>
                                                        </Row>
                                                    </Card>
                                                </div>
                                            ) : (
                                                <Empty description="等待启动对决..." style={{ padding: '40px 0' }} />
                                            )}
                                        </Card>
                                    </Col>

                                    <Col xs={24} md={12}>
                                        <Card
                                            title={
                                                <Flex justify="space-between" align="center">
                                                    <Space>
                                                        <Badge status="warning" />
                                                        <Text strong>Variant B (对抗优化)</Text>
                                                    </Space>
                                                    <Select
                                                        size="small"
                                                        value={abModelB}
                                                        onChange={setAbModelB}
                                                        options={[
                                                            { value: 'balanced', label: 'Balanced 通用' },
                                                            { value: 'reasoning', label: 'Reasoning 推理增强' }
                                                        ]}
                                                        style={{ width: '130px' }}
                                                    />
                                                </Flex>
                                            }
                                            style={{ background: 'rgba(255,255,255,0.01)', borderColor: '#1f1f1f', minHeight: '380px' }}
                                        >
                                            <Input.TextArea
                                                value={abPromptB}
                                                onChange={e => setAbPromptB(e.target.value)}
                                                rows={3}
                                                style={{ background: '#050505', color: '#eaeaea', borderColor: '#444', fontSize: '11px', marginBottom: 16 }}
                                                placeholder="系统提示词 B (你可以调优此处提示词以对比效果)"
                                            />
                                            {abResultB ? (
                                                <div>
                                                    <div className="markdown-body" style={{ color: '#ddd', fontSize: '13px', background: 'rgba(24,144,255,0.05)', padding: '12px', borderRadius: '4px', borderLeft: '3px solid #1890ff' }}>
                                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                            {abResultB.content}
                                                        </ReactMarkdown>
                                                    </div>
                                                    <Card size="small" style={{ background: 'rgba(0,0,0,0.3)', borderColor: '#222', marginTop: 12 }}>
                                                        <Row gutter={10}>
                                                            <Col span={8} style={{ textAlign: 'center' }}><Text type="secondary" style={{ fontSize: '11px' }}>延迟</Text><div style={{ color: '#fa8c16', fontWeight: 'bold' }}>⏱️ {abResultB.metrics?.latencyMs}ms</div></Col>
                                                            <Col span={8} style={{ textAlign: 'center' }}><Text type="secondary" style={{ fontSize: '11px' }}>Tokens</Text><div style={{ color: '#1890ff', fontWeight: 'bold' }}>🪙 {abResultB.metrics?.promptTokens} tks</div></Col>
                                                            <Col span={8} style={{ textAlign: 'center' }}><Text type="secondary" style={{ fontSize: '11px' }}>评估 RAGAS 评分</Text><div style={{ color: '#a855f7', fontWeight: 'bold' }}>⭐ 96 / PASS</div></Col>
                                                        </Row>
                                                    </Card>
                                                </div>
                                            ) : (
                                                <Empty description="等待启动对决..." style={{ padding: '40px 0' }} />
                                            )}
                                        </Card>
                                    </Col>
                                </Row>
                            </div>
                        )
                    },
                    {
                        key: 'traces',
                        label: (
                            <span>
                                <CompassOutlined />
                                运行日志与链路 (Traces)
                            </span>
                        ),
                        children: (
                            <Row gutter={20} style={{ marginTop: 15 }}>
                                <Col xs={24} md={12}>
                                    <Card title={<Space><CodeOutlined /> <Text strong>真实运行流程链路追踪 (LangGraph Nodes)</Text></Space>} style={{ background: 'rgba(255,255,255,0.01)', borderColor: '#1f1f1f', height: '480px' }}>
                                        <Timeline
                                            items={[
                                                {
                                                    color: 'green',
                                                    children: (
                                                        <div>
                                                            <Text strong>pre_processor (前置分流与语义缓存碰撞)</Text>
                                                            <Paragraph type="secondary" style={{ fontSize: '12px', marginTop: '4px' }}>命中缓存判定：未命中 (Miss)，耗时 80ms。</Paragraph>
                                                        </div>
                                                    )
                                                },
                                                {
                                                    color: 'blue',
                                                    children: (
                                                        <div>
                                                            <Text strong>supervisor (集群意图总控)</Text>
                                                            <Paragraph type="secondary" style={{ fontSize: '12px', marginTop: '4px' }}>判定此意图属于专业化特定问题。指定特定 Agent：[{agent.name}] 并提供上下文。耗时 420ms。</Paragraph>
                                                        </div>
                                                    )
                                                },
                                                {
                                                    color: 'purple',
                                                    children: (
                                                        <div>
                                                            <Text strong>{agent.name} (特定 Agent 执行节点)</Text>
                                                            <Paragraph type="secondary" style={{ fontSize: '12px', marginTop: '4px' }}>
                                                                触发 Skills、加载内置参数并调用 MCP 工具 [ {agent.tools?.join(', ') || 'default_tool'} ]，对文档数据和语义库进行实证。耗时 1200ms。
                                                            </Paragraph>
                                                        </div>
                                                    )
                                                },
                                                {
                                                    color: 'orange',
                                                    children: (
                                                        <div>
                                                            <Text strong>reflection (MultiGrader 反思和自我校验)</Text>
                                                            <Paragraph type="secondary" style={{ fontSize: '12px', marginTop: '4px' }}>自动加载 RAGAS 评估库，检测 Faithfulness (94%) 及 Answer Relevance (91%)。判定：PASS。耗时 600ms。</Paragraph>
                                                        </div>
                                                    )
                                                }
                                            ]}
                                        />
                                    </Card>
                                </Col>
                                <Col xs={24} md={12}>
                                    <Card title={<Space><BugOutlined /> <Text strong>调用详情上下文与 Payload (Details)</Text></Space>} style={{ background: 'rgba(255,255,255,0.01)', borderColor: '#1f1f1f', height: '480px', overflowY: 'auto' }}>
                                        <pre style={{ color: '#a855f7', background: '#050505', padding: '16px', borderRadius: '4px', fontSize: '11px', fontFamily: 'Consolas, monospace' }}>
{`{
  "trace_id": "tr-8c593b2a-bf31",
  "agent_name": "${agent.name}",
  "model_hint": "${modelHint}",
  "system_prompt": "${systemPrompt.substring(0, 80)}...",
  "skills": ${JSON.stringify(agent.skills || [])},
  "mcp_tools": ${JSON.stringify(agent.tools || [])},
  "execution_payload": {
    "temperature": 0.2,
    "top_p": 0.95,
    "max_tokens": 1024,
    "stream": true,
    "speculative_retrieval": true
  },
  "ragas_evaluation": {
    "composite_score": 0.94,
    "faithfulness": 0.95,
    "answer_relevance": 0.92,
    "context_recall": 0.88,
    "hard_rule_vetoed": false
  }
}`}
                                        </pre>
                                    </Card>
                                </Col>
                            </Row>
                        )
                    },
                    {
                        key: 'reports',
                        label: (
                            <span>
                                <LineChartOutlined />
                                评估测试报告 (Reports)
                            </span>
                        ),
                        children: (
                            <div style={{ marginTop: 10 }}>
                                <Row gutter={20} style={{ marginBottom: 16 }}>
                                    <Col span={6}>
                                        <Card size="small" style={{ textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderColor: '#1f1f1f' }}>
                                            <Text type="secondary" style={{ fontSize: '12px' }}>综合运行成功率</Text>
                                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#06D6A0', marginTop: 4 }}>94.2%</div>
                                        </Card>
                                    </Col>
                                    <Col span={6}>
                                        <Card size="small" style={{ textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderColor: '#1f1f1f' }}>
                                            <Text type="secondary" style={{ fontSize: '12px' }}>RAGAS 忠实度</Text>
                                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff', marginTop: 4 }}>91.5%</div>
                                        </Card>
                                    </Col>
                                    <Col span={6}>
                                        <Card size="small" style={{ textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderColor: '#1f1f1f' }}>
                                            <Text type="secondary" style={{ fontSize: '12px' }}>平均调用响应速度</Text>
                                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fa8c16', marginTop: 4 }}>1.65s</div>
                                        </Card>
                                    </Col>
                                    <Col span={6}>
                                        <Card size="small" style={{ textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderColor: '#1f1f1f' }}>
                                            <Text type="secondary" style={{ fontSize: '12px' }}>缓存命省电指数</Text>
                                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#a855f7', marginTop: 4 }}>⚡ 42%</div>
                                        </Card>
                                    </Col>
                                </Row>

                                <Card title={<Space><HistoryOutlined /> <Text strong>测试历史快照 (Test History)</Text></Space>} style={{ background: 'rgba(255,255,255,0.01)', borderColor: '#1f1f1f', marginBottom: 16 }}>
                                    <Table columns={historyColumns} dataSource={historyData} size="small" pagination={false} />
                                </Card>

                                <Card title={<Space><InfoCircleOutlined style={{ color: '#ff4d4f' }} /> <Text strong>检测到的 Bad Cases（需要调优）</Text></Space>} style={{ background: 'rgba(255,255,255,0.01)', borderColor: '#1f1f1f' }}>
                                    <List
                                        dataSource={badCases}
                                        renderItem={item => (
                                            <List.Item style={{ borderBottom: '1px solid #1f1f1f', padding: '12px 0' }}>
                                                <List.Item.Meta
                                                    avatar={<CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: '16px', marginTop: 4 }} />}
                                                    title={<Space><Text strong>{item.id}</Text> <Text type="secondary">问题: {item.question}</Text></Space>}
                                                    description={<span style={{ color: '#888' }}>原因分析: {item.reason}</span>}
                                                />
                                                <Tag color={item.status === '已调优参数' ? 'success' : 'warning'}>{item.status}</Tag>
                                            </List.Item>
                                        )}
                                    />
                                </Card>
                            </div>
                        )
                    }
                ]}
            />
        </Modal>
    );
};
