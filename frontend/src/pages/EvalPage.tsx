import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Space, Card, Progress, App, Modal, Form, Input, Select, Tabs, Statistic, Row, Col, Flex, Typography } from 'antd';
import { BugOutlined, LineChartOutlined, DatabaseOutlined, PlayCircleOutlined, PlusOutlined, FileSearchOutlined, TrophyOutlined, ThunderboltOutlined, DollarOutlined, DownloadOutlined, ExperimentOutlined, SafetyCertificateOutlined, AimOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { evalApi } from '../services/evalApi';
import { knowledgeApi } from '../services/knowledgeApi';
import type { EvaluationSet, EvaluationReport, KnowledgeBase } from '../types';

const { TabPane } = Tabs;
const { Text, Title, Paragraph } = Typography;

// ============================================================
//  RAGAS Benchmark Metric Definitions
// ============================================================
const RAGAS_METRICS = [
    {
        key: 'faithfulness',
        name: 'Faithfulness (忠实度)',
        icon: <SafetyCertificateOutlined />,
        color: '#52c41a',
        description: '衡量 AI 回答是否完全基于检索到的上下文，不产生幻觉。',
        formula: 'Faithful Statements / Total Statements',
        benchmark: { excellent: 0.9, good: 0.7, poor: 0.5 }
    },
    {
        key: 'answer_relevance',
        name: 'Answer Relevance (答案相关性)',
        icon: <AimOutlined />,
        color: '#1890ff',
        description: '评估 AI 回答与用户问题的相关程度，从多角度检测偏题。',
        formula: 'Mean Cosine Sim(Generated Q, Original Q)',
        benchmark: { excellent: 0.9, good: 0.7, poor: 0.5 }
    },
    {
        key: 'context_precision',
        name: 'Context Precision (上下文精确度)',
        icon: <ExperimentOutlined />,
        color: '#722ed1',
        description: '评估检索到的上下文块中有多少是与问题真正相关的（信号/噪声比）。',
        formula: 'Relevant Chunks / Total Retrieved Chunks',
        benchmark: { excellent: 0.85, good: 0.65, poor: 0.4 }
    },
    {
        key: 'context_recall',
        name: 'Context Recall (上下文召回率)',
        icon: <FileSearchOutlined />,
        color: '#eb2f96',
        description: '评估 Ground Truth 中的关键信息有多少被检索系统成功召回。',
        formula: 'GT Sentences in Context / Total GT Sentences',
        benchmark: { excellent: 0.85, good: 0.65, poor: 0.4 }
    }
];

// ============================================================
//  Report Export — Generates an HTML report and triggers download
// ============================================================
function generateReportHTML(
    reports: EvaluationReport[],
    leaderboard: any[],
    badCases: any[],
    exportTime: string
): string {
    const completedReports = reports.filter(r => r.status === 'completed');
    const totalEvals = completedReports.length;
    const avgScore = totalEvals > 0 ? (completedReports.reduce((s, r) => s + r.total_score, 0) / totalEvals) : 0;
    const totalCost = completedReports.reduce((s, r) => s + (r.cost || 0), 0);
    const avgLatency = totalEvals > 0 ? (completedReports.reduce((s, r) => s + (r.latency_ms || 0), 0) / totalEvals) : 0;

    // Build model comparison table
    const modelRows = leaderboard.map((m, i) => `
        <tr>
            <td style="text-align:center;font-weight:bold;">${i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}</td>
            <td><strong>${m.model}</strong></td>
            <td style="text-align:center;">${(m.avgScore * 100).toFixed(1)}%</td>
            <td style="text-align:center;">${m.faithfulness.toFixed(3)}</td>
            <td style="text-align:center;">${m.relevance.toFixed(3)}</td>
            <td style="text-align:center;">${Math.round(m.avgLatency)}ms</td>
            <td style="text-align:center;">$${m.avgCost.toFixed(4)}</td>
            <td style="text-align:center;">${m.count}</td>
        </tr>
    `).join('');

    // Build per-report detail table
    const reportRows = completedReports.map(r => `
        <tr>
            <td>${new Date(r.created_at).toLocaleString()}</td>
            <td><code>${r.model_name}</code></td>
            <td style="text-align:center;">${(r.total_score * 100).toFixed(1)}%</td>
            <td style="text-align:center;">${r.faithfulness.toFixed(3)}</td>
            <td style="text-align:center;">${r.answer_relevance.toFixed(3)}</td>
            <td style="text-align:center;">${r.context_precision.toFixed(3)}</td>
            <td style="text-align:center;">${r.context_recall.toFixed(3)}</td>
            <td style="text-align:center;">${Math.round(r.latency_ms)}ms</td>
            <td style="text-align:center;">$${(r.cost || 0).toFixed(4)}</td>
            <td style="text-align:center;">${r.token_usage || 0}</td>
        </tr>
    `).join('');

    // Build Bad Cases section
    const badCaseRows = badCases.map(bc => `
        <tr>
            <td>${bc.question}</td>
            <td style="color:#ff4d4f;">${bc.bad_answer}</td>
            <td>${bc.reason || '-'}</td>
            <td><span class="badge badge-${bc.status === 'fixed' ? 'success' : bc.status === 'reviewed' ? 'warning' : 'danger'}">${bc.status?.toUpperCase()}</span></td>
        </tr>
    `).join('');

    // Build detailed QA analysis for top model
    let qaDetail = '';
    if (leaderboard.length > 0 && completedReports.length > 0) {
        const bestModel = leaderboard[0].model;
        const bestReport = completedReports.find(r => r.model_name === bestModel);
        if (bestReport) {
            try {
                const details = JSON.parse(bestReport.details_json || '[]');
                const qaRows = details.map((d: any, i: number) => `
                    <tr>
                        <td style="text-align:center;">${i + 1}</td>
                        <td>${d.question}</td>
                        <td>${d.ground_truth}</td>
                        <td>${d.answer}</td>
                        <td style="text-align:center;color:${d.faithfulness > 0.7 ? '#52c41a' : '#ff4d4f'}">${d.faithfulness}</td>
                        <td style="text-align:center;color:${d.relevance > 0.7 ? '#52c41a' : '#ff4d4f'}">${d.relevance}</td>
                    </tr>
                `).join('');
                qaDetail = `
                    <h2>📋 最优模型 QA 逐题分析 — ${bestModel}</h2>
                    <table>
                        <thead><tr>
                            <th>#</th><th>问题 (Question)</th><th>标准答案 (Ground Truth)</th><th>AI 回答</th><th>Faithfulness</th><th>Relevance</th>
                        </tr></thead>
                        <tbody>${qaRows}</tbody>
                    </table>
                `;
            } catch { }
        }
    }

    // Score level
    const scoreLevel = avgScore > 0.8 ? '优秀 (Excellent)' : avgScore > 0.6 ? '良好 (Good)' : avgScore > 0.4 ? '待改进 (Needs Improvement)' : '不合格 (Poor)';
    const scoreBadge = avgScore > 0.8 ? '#52c41a' : avgScore > 0.6 ? '#1890ff' : avgScore > 0.4 ? '#faad14' : '#ff4d4f';

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HiveMind RAG 评估综合报告</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', sans-serif; background: #0d1117; color: #c9d1d9; padding: 40px; line-height: 1.7; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 40px; padding: 40px; background: linear-gradient(135deg, #161b22 0%, #1a2332 100%); border-radius: 16px; border: 1px solid rgba(48,54,61,0.8); }
        .header h1 { font-size: 28px; color: #58a6ff; margin-bottom: 8px; }
        .header .subtitle { color: #8b949e; font-size: 14px; }
        .header .score-badge { display: inline-block; margin-top: 16px; padding: 8px 24px; border-radius: 20px; font-size: 20px; font-weight: bold; color: white; }
        h2 { color: #58a6ff; font-size: 20px; margin: 36px 0 16px; padding-bottom: 8px; border-bottom: 1px solid #21262d; }
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
        .metric-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; text-align: center; }
        .metric-card .value { font-size: 28px; font-weight: bold; color: #58a6ff; }
        .metric-card .label { font-size: 12px; color: #8b949e; margin-top: 4px; }
        .ragas-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px; }
        .ragas-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }
        .ragas-card .metric-name { font-size: 15px; font-weight: bold; margin-bottom: 6px; }
        .ragas-card .metric-desc { font-size: 12px; color: #8b949e; margin-bottom: 10px; }
        .ragas-card .metric-formula { font-family: 'Courier New', monospace; font-size: 11px; color: #79c0ff; background: #0d1117; padding: 4px 8px; border-radius: 4px; display: inline-block; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 24px; background: #161b22; border-radius: 8px; overflow: hidden; }
        th { background: #21262d; color: #c9d1d9; padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; }
        td { padding: 10px 16px; border-bottom: 1px solid #21262d; font-size: 13px; }
        tr:last-child td { border-bottom: none; }
        code { background: #1f2937; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #79c0ff; }
        .badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .badge-success { background: rgba(82,196,26,0.2); color: #52c41a; }
        .badge-warning { background: rgba(250,173,20,0.2); color: #faad14; }
        .badge-danger { background: rgba(255,77,79,0.2); color: #ff4d4f; }
        .footer { text-align: center; margin-top: 48px; padding: 24px; color: #484f58; font-size: 12px; border-top: 1px solid #21262d; }
        @media print { body { background: white; color: #1f2328; } .header { background: #f6f8fa; } h2 { color: #0969da; } table, .metric-card, .ragas-card { background: #f6f8fa; border-color: #d0d7de; } th { background: #eee; color: #333; } td { border-color: #d0d7de; color: #1f2328; } .footer { color: #999; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🧠 HiveMind RAG 评估综合报告</h1>
        <div class="subtitle">基于 RAGAS (Retrieval Augmented Generation Assessment) 框架的全面质量评估</div>
        <div class="subtitle" style="margin-top:4px;">报告生成时间: ${exportTime}</div>
        <div class="score-badge" style="background:${scoreBadge}">综合评级: ${scoreLevel}　—　${(avgScore * 100).toFixed(1)}%</div>
    </div>

    <h2>📊 评估概览 (Executive Summary)</h2>
    <div class="metrics-grid">
        <div class="metric-card"><div class="value">${totalEvals}</div><div class="label">评测总次数</div></div>
        <div class="metric-card"><div class="value">${(avgScore * 100).toFixed(1)}%</div><div class="label">平均综合得分</div></div>
        <div class="metric-card"><div class="value">${Math.round(avgLatency)}ms</div><div class="label">平均响应延迟</div></div>
        <div class="metric-card"><div class="value">$${totalCost.toFixed(4)}</div><div class="label">累计评估成本</div></div>
    </div>

    <h2>🔬 RAGAS 评估指标体系说明</h2>
    <div class="ragas-grid">
        <div class="ragas-card">
            <div class="metric-name" style="color:#52c41a">✅ Faithfulness (忠实度)</div>
            <div class="metric-desc">衡量 AI 回答是否完全基于检索到的上下文，不产生幻觉 (Hallucination)。</div>
            <div class="metric-formula">Score = Faithful Statements / Total Statements</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:#1890ff">🎯 Answer Relevance (答案相关性)</div>
            <div class="metric-desc">评估 AI 回答与用户问题的相关程度，从多角度检测偏题和冗余信息。</div>
            <div class="metric-formula">Score = Mean Cosine Sim(Generated Q, Original Q)</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:#722ed1">🔍 Context Precision (上下文精确度)</div>
            <div class="metric-desc">评估检索到的上下文块中有多少是与问题真正相关的（信噪比）。</div>
            <div class="metric-formula">Score = Relevant Chunks / Total Retrieved Chunks</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:#eb2f96">📖 Context Recall (上下文召回率)</div>
            <div class="metric-desc">评估 Ground Truth 中的关键信息有多少被检索系统成功召回。</div>
            <div class="metric-formula">Score = GT Sentences in Context / Total GT Sentences</div>
        </div>
    </div>

    <h2>🏆 多模型性能排行 (Model Arena)</h2>
    <table>
        <thead><tr>
            <th style="text-align:center;">排名</th><th>模型</th><th style="text-align:center;">综合得分</th>
            <th style="text-align:center;">Faithfulness</th><th style="text-align:center;">Relevance</th>
            <th style="text-align:center;">平均延迟</th><th style="text-align:center;">单位成本</th><th style="text-align:center;">评测轮次</th>
        </tr></thead>
        <tbody>${modelRows}</tbody>
    </table>

    <h2>📑 完整评估报告列表</h2>
    <table>
        <thead><tr>
            <th>时间</th><th>模型</th><th style="text-align:center;">综合分</th>
            <th style="text-align:center;">Faith.</th><th style="text-align:center;">Relev.</th>
            <th style="text-align:center;">C.Prec.</th><th style="text-align:center;">C.Recall</th>
            <th style="text-align:center;">延迟</th><th style="text-align:center;">成本</th><th style="text-align:center;">Tokens</th>
        </tr></thead>
        <tbody>${reportRows}</tbody>
    </table>

    ${qaDetail}

    ${badCases.length > 0 ? `
    <h2>🐛 Bad Cases 问题追踪 (${badCases.length} 条)</h2>
    <table>
        <thead><tr><th>问题</th><th>差评答案</th><th>原因分析</th><th>状态</th></tr></thead>
        <tbody>${badCaseRows}</tbody>
    </table>
    ` : ''}

    <h2>📐 评估方法论 (Methodology)</h2>
    <div class="ragas-card" style="margin-bottom:24px;">
        <div class="metric-name" style="color:#58a6ff;">RAGAS (Retrieval Augmented Generation Assessment)</div>
        <div class="metric-desc" style="font-size:13px;line-height:1.8;">
            本报告遵循 <strong>RAGAS</strong> 开源评估框架的核心方法论，结合 <strong>LLM-as-a-Judge</strong> 模式进行自动化质量评测：<br/>
            <strong>1. Ground Truth 生成</strong> — 从知识库原始文档中提取文本块，使用 LLM 生成符合真实场景的 QA 对。<br/>
            <strong>2. RAG Pipeline 运行</strong> — 对每个问题执行完整的 检索→重排→生成 流程，记录回答、上下文、延迟和 Token 用量。<br/>
            <strong>3. LLM Judge 评分</strong> — 使用独立的 Judge LLM 对每组结果进行多维度打分 (Faithfulness, Relevance, Precision, Recall)。<br/>
            <strong>4. 统计汇总</strong> — 对所有 QA 对的分数取平均，生成综合评分。低分 Case 自动进入 Bad Case 追踪。<br/>
            <br/>
            <em>参考文献: Shahul Es et al., "RAGAS: Automated Evaluation of Retrieval Augmented Generation", 2023. arXiv:2309.15217</em>
        </div>
    </div>

    <div class="footer">
        HiveMind AI Platform · RAG Quality Assessment Report · Generated at ${exportTime}<br/>
        Powered by RAGAS Methodology · LLM-as-a-Judge Scoring · Multi-Model Arena Benchmarking
    </div>
</div>
</body>
</html>`;
}


export const EvalPage: React.FC = () => {
    const { message } = App.useApp();
    const [sets, setSets] = useState<EvaluationSet[]>([]);
    const [reports, setReports] = useState<EvaluationReport[]>([]);
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [badCases, setBadCases] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [form] = Form.useForm();
    const [runForm] = Form.useForm();
    const [selectedReport, setSelectedReport] = useState<EvaluationReport | null>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isRunModalOpen, setIsRunModalOpen] = useState(false);
    const [activeSetId, setActiveSetId] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [setsRes, reportsRes, kbsRes, badCasesRes] = await Promise.all([
                evalApi.getTestsets(),
                evalApi.getReports(),
                knowledgeApi.listKBs(),
                evalApi.getBadCases()
            ]);
            setSets(setsRes.data.data || []);
            setReports(reportsRes.data.data || []);
            setKbs(kbsRes.data.data || []);
            setBadCases(badCasesRes.data.data || []);
        } catch (err) {
            message.error("数据加载失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleCreateSet = async (values: any) => {
        try {
            await evalApi.createTestset(values.kb_id, values.name, values.count);
            message.success("测试集生成任务已启动，请稍后刷新查看");
            setIsModalOpen(false);
            form.resetFields();
            fetchData(); // Refresh to catch potential updates
        } catch (err) {
            message.error("创建失败");
        }
    };

    const handleRunEval = (setId: string) => {
        setActiveSetId(setId);
        setIsRunModalOpen(true);
    };

    const confirmRunEval = async (values: any) => {
        if (!activeSetId) return;
        try {
            await evalApi.runEvaluation(activeSetId, values.model_name);
            message.success(`针对模型 ${values.model_name} 的评估任务已启动`);
            setIsRunModalOpen(false);
        } catch (err) {
            message.error("启动失败");
        }
    };

    const viewDetails = (report: EvaluationReport) => {
        setSelectedReport(report);
        setIsDetailOpen(true);
    };

    // Calculate Leaderboard (Arena)
    const getLeaderboard = useCallback(() => {
        const modelStats: Record<string, any> = {};
        reports.filter(r => r.status === 'completed').forEach(r => {
            const m = r.model_name || 'unknown';
            if (!modelStats[m]) {
                modelStats[m] = {
                    model: m,
                    avgScore: 0,
                    avgLatency: 0,
                    avgCost: 0,
                    count: 0,
                    faithfulness: 0,
                    relevance: 0
                };
            }
            modelStats[m].avgScore += r.total_score;
            modelStats[m].avgLatency += (r.latency_ms || 0);
            modelStats[m].avgCost += (r.cost || 0);
            modelStats[m].faithfulness += r.faithfulness;
            modelStats[m].relevance += r.answer_relevance;
            modelStats[m].count += 1;
        });

        return Object.values(modelStats).map((s: any) => ({
            ...s,
            avgScore: s.avgScore / s.count,
            avgLatency: s.avgLatency / s.count,
            avgCost: s.avgCost / s.count,
            faithfulness: s.faithfulness / s.count,
            relevance: s.relevance / s.count
        })).sort((a, b) => b.avgScore - a.avgScore);
    }, [reports]);

    // ── Export Report ──
    const handleExportReport = useCallback(() => {
        const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
        const lb = getLeaderboard();
        const html = generateReportHTML(reports, lb, badCases, now);

        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `HiveMind_RAG_Evaluation_Report_${new Date().toISOString().slice(0, 10)}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        message.success('综合评估报告已导出！请在浏览器中打开 HTML 文件查看，也可直接打印为 PDF。');
    }, [reports, badCases, sets, getLeaderboard, message]);

    const setColumns = [
        { title: '测试集名称', dataIndex: 'name', key: 'name' },
        {
            title: '所属知识库',
            dataIndex: 'kb_id',
            key: 'kb',
            render: (id: string) => kbs.find(kb => kb.id === id)?.name || id
        },
        { title: '创建时间', dataIndex: 'created_at', key: 'time', render: (t: string) => new Date(t).toLocaleString() },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: EvaluationSet) => (
                <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    size="small"
                    onClick={() => handleRunEval(record.id)}
                >
                    运行评估
                </Button>
            )
        }
    ];

    const reportColumns = [
        { title: '评估时间', dataIndex: 'created_at', key: 'time', render: (t: string) => new Date(t).toLocaleString() },
        {
            title: '模型 (Model)',
            dataIndex: 'model_name',
            key: 'model',
            render: (m: string) => <Tag color="blue">{m}</Tag>
        },
        {
            title: '总评分',
            dataIndex: 'total_score',
            key: 'score',
            render: (score: number) => (
                <Progress
                    percent={Math.round(score * 100)}
                    size="small"
                    format={p => `${p}%`}
                    strokeColor={score > 0.7 ? '#52c41a' : score > 0.4 ? '#faad14' : '#f5222d'}
                />
            )
        },
        {
            title: '响应延迟',
            dataIndex: 'latency_ms',
            key: 'latency',
            render: (ms: number) => ms ? <Tag icon={<ThunderboltOutlined />}>{Math.round(ms)}ms</Tag> : '-'
        },
        {
            title: '预估成本',
            dataIndex: 'cost',
            key: 'cost',
            render: (c: number) => c ? <Tag color="gold" icon={<DollarOutlined />}>${c.toFixed(4)}</Tag> : '-'
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (s: string) => {
                const colors = { running: 'processing', completed: 'success', failed: 'error' };
                return <Tag color={(colors as any)[s] || 'default'}>{s.toUpperCase()}</Tag>;
            }
        },
        {
            title: '详情',
            key: 'action',
            render: (_: any, record: EvaluationReport) => (
                <Button
                    size="small"
                    icon={<FileSearchOutlined />}
                    onClick={() => viewDetails(record)}
                >
                    查看明细
                </Button>
            )
        }
    ];

    const arenaColumns = [
        {
            title: '排名',
            key: 'rank',
            width: 80,
            render: (_: any, __: any, index: number) => (
                <Text style={{ fontSize: index === 0 ? '20px' : '14px', fontWeight: 'bold' }}>
                    {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : index + 1}
                </Text>
            )
        },
        {
            title: 'AI 模型',
            dataIndex: 'model',
            key: 'model',
            render: (m: string) => <Text strong style={{ fontSize: '16px' }}>{m}</Text>
        },
        {
            title: '综合得分 (ELO-like)',
            dataIndex: 'avgScore',
            key: 'score',
            sorter: (a: any, b: any) => a.avgScore - b.avgScore,
            render: (s: number) => <Progress percent={Math.round(s * 100)} strokeColor="#1890ff" />
        },
        {
            title: 'Faithfulness',
            dataIndex: 'faithfulness',
            key: 'f',
            render: (s: number) => <Tag color="green">{s.toFixed(2)}</Tag>
        },
        {
            title: 'Relevance',
            dataIndex: 'relevance',
            key: 'r',
            render: (s: number) => <Tag color="purple">{s.toFixed(2)}</Tag>
        },
        {
            title: '平均延迟',
            dataIndex: 'avgLatency',
            key: 'lat',
            render: (s: number) => <Text type="secondary">{Math.round(s)}ms</Text>
        },
        {
            title: '单位成本 (估计)',
            dataIndex: 'avgCost',
            key: 'cost',
            render: (s: number) => <Tag color="gold">${s.toFixed(4)}</Tag>
        },
        { title: '评测轮次', dataIndex: 'count', key: 'count' }
    ];

    const renderDetails = () => {
        if (!selectedReport) return null;
        let details: any[] = [];
        try {
            details = JSON.parse(selectedReport.details_json || '[]');
        } catch (e) { }

        return (
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Card size="small" style={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', backdropFilter: 'blur(10px)' }}>
                    <Row gutter={16}>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>模型</span>} value={selectedReport.model_name} valueStyle={{ fontSize: 14, color: '#fff' }} /></Col>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>延迟</span>} value={selectedReport.latency_ms} suffix={<span style={{ fontSize: 12 }}>ms</span>} valueStyle={{ fontSize: 14, color: '#fff' }} /></Col>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>成本</span>} value={selectedReport.cost} prefix="$" precision={4} valueStyle={{ fontSize: 14, color: '#faad14' }} /></Col>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>Token</span>} value={selectedReport.token_usage || 0} valueStyle={{ fontSize: 14, color: '#fff' }} /></Col>
                    </Row>
                </Card>

                {/* RAGAS Metrics Summary for this report */}
                <Card size="small" style={{ borderRadius: 12, background: 'rgba(20,20,20,0.4)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <Row gutter={16}>
                        <Col span={6}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Faithfulness</span>} value={selectedReport.faithfulness} precision={3}
                                valueStyle={{ fontSize: 16, color: selectedReport.faithfulness > 0.7 ? '#52c41a' : '#faad14' }} />
                        </Col>
                        <Col span={6}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Relevance</span>} value={selectedReport.answer_relevance} precision={3}
                                valueStyle={{ fontSize: 16, color: selectedReport.answer_relevance > 0.7 ? '#52c41a' : '#faad14' }} />
                        </Col>
                        <Col span={6}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Ctx Precision</span>} value={selectedReport.context_precision} precision={3}
                                valueStyle={{ fontSize: 16, color: selectedReport.context_precision > 0.7 ? '#52c41a' : '#faad14' }} />
                        </Col>
                        <Col span={6}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Ctx Recall</span>} value={selectedReport.context_recall} precision={3}
                                valueStyle={{ fontSize: 16, color: selectedReport.context_recall > 0.7 ? '#52c41a' : '#faad14' }} />
                        </Col>
                    </Row>
                </Card>

                <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: 8 }}>
                    {details.map((item, idx) => (
                        <Card
                            key={idx}
                            size="small"
                            style={{ marginBottom: 16, borderRadius: 12, border: '1px solid rgba(255,255,255,0.05)' }}
                            title={<Text style={{ fontSize: 13, color: 'rgba(255,255,255,0.45)' }}>Case #{idx + 1}</Text>}
                            extra={
                                <Space size={4}>
                                    <Tag color={item.faithfulness > 0.7 ? 'success' : 'error'} bordered={false} style={{ fontSize: 10 }}>F: {item.faithfulness}</Tag>
                                    <Tag color={item.relevance > 0.7 ? 'success' : 'error'} bordered={false} style={{ fontSize: 10 }}>R: {item.relevance}</Tag>
                                </Space>
                            }
                        >
                            <div style={{ marginBottom: 12 }}>
                                <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>Q</Text>
                                <Text strong>{item.question}</Text>
                            </div>
                            <div style={{ marginBottom: 12, padding: '10px 14px', background: 'rgba(24,144,255,0.05)', borderRadius: 8, border: '1px solid rgba(24,144,255,0.1)' }}>
                                <Text style={{ fontSize: 11, color: '#1890ff', display: 'block', marginBottom: 4 }}>Standard Answer</Text>
                                <Text style={{ fontSize: 13, opacity: 0.85 }}>{item.ground_truth}</Text>
                            </div>
                            <div style={{ marginBottom: 12, padding: '10px 14px', background: 'rgba(82,196,26,0.05)', borderRadius: 8, border: '1px solid rgba(82,196,26,0.1)' }}>
                                <Text style={{ fontSize: 11, color: '#52c41a', display: 'block', marginBottom: 4 }}>Model Generated</Text>
                                <Text style={{ fontSize: 13 }}>{item.answer}</Text>
                            </div>
                            {(item.context_precision || item.context_recall) && (
                                <Flex gap={8}>
                                    <Tag color="purple" bordered={false} style={{ fontSize: 10 }}>Precision: {item.context_precision || '-'}</Tag>
                                    <Tag color="magenta" bordered={false} style={{ fontSize: 10 }}>Recall: {item.context_recall || '-'}</Tag>
                                </Flex>
                            )}
                        </Card>
                    ))}
                </div>
            </Space>
        );
    };

    const renderRagasBenchmark = () => {
        const lb = getLeaderboard();
        const completedReports = reports.filter(r => r.status === 'completed');
        const avgMetrics = {
            faithfulness: completedReports.length > 0 ? completedReports.reduce((s, r) => s + r.faithfulness, 0) / completedReports.length : 0,
            answer_relevance: completedReports.length > 0 ? completedReports.reduce((s, r) => s + r.answer_relevance, 0) / completedReports.length : 0,
            context_precision: completedReports.length > 0 ? completedReports.reduce((s, r) => s + r.context_precision, 0) / completedReports.length : 0,
            context_recall: completedReports.length > 0 ? completedReports.reduce((s, r) => s + r.context_recall, 0) / completedReports.length : 0,
        };

        const metricColors = {
            faithfulness: 'hsl(145, 63%, 49%)',
            answer_relevance: 'hsl(210, 100%, 60%)',
            context_precision: 'hsl(265, 60%, 60%)',
            context_recall: 'hsl(330, 80%, 60%)'
        };

        return (
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                {/* RAGAS Metrics Overview - Bento/Card Style */}
                <div>
                    <Flex align="center" gap={8} style={{ marginBottom: 16 }}>
                        <ExperimentOutlined style={{ color: '#58a6ff', fontSize: 18 }} />
                        <Title level={5} style={{ margin: 0, fontWeight: 500 }}>RAGAS 综合质量看板</Title>
                    </Flex>
                    <Row gutter={[20, 20]}>
                        {RAGAS_METRICS.map(metric => {
                            const val = (avgMetrics as any)[metric.key] || 0;
                            const bm = metric.benchmark;
                            const level = val >= bm.excellent ? 'Excellent' : val >= bm.good ? 'Good' : val >= bm.poor ? 'Fair' : 'Poor';
                            const baseColor = (metricColors as any)[metric.key];

                            return (
                                <Col span={6} key={metric.key}>
                                    <Card
                                        size="small"
                                        bordered={false}
                                        style={{
                                            borderRadius: 16,
                                            background: `linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)`,
                                            border: '1px solid rgba(255,255,255,0.05)',
                                            position: 'relative',
                                            overflow: 'hidden'
                                        }}
                                    >
                                        <div style={{
                                            position: 'absolute',
                                            top: -20,
                                            right: -20,
                                            width: 80,
                                            height: 80,
                                            background: `${baseColor}11`,
                                            borderRadius: '50%',
                                            filter: 'blur(30px)'
                                        }} />

                                        <Space style={{ marginBottom: 16 }}>
                                            <div style={{
                                                width: 32, height: 32, borderRadius: 8,
                                                background: `${baseColor}22`,
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                color: baseColor
                                            }}>
                                                {metric.icon}
                                            </div>
                                            <Text strong style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>{metric.name.split(' ')[0]}</Text>
                                        </Space>

                                        <div style={{ marginBottom: 8 }}>
                                            <Flex justify="space-between" align="baseline">
                                                <Title level={3} style={{ margin: 0, color: '#fff', fontWeight: 600 }}>{Math.round(val * 100)}<span style={{ fontSize: 14, opacity: 0.45 }}>%</span></Title>
                                                <Tag color={val >= bm.good ? 'success' : 'warning'} bordered={false} style={{ margin: 0, background: 'rgba(255,255,255,0.05)', color: baseColor }}>{level}</Tag>
                                            </Flex>
                                        </div>

                                        <Progress
                                            percent={Math.round(val * 100)}
                                            strokeColor={baseColor}
                                            showInfo={false}
                                            size={4}
                                            style={{ margin: '8px 0' }}
                                        />

                                        <Paragraph type="secondary" style={{ fontSize: 11, marginBottom: 0, opacity: 0.6, lineHeight: 1.4 }}>
                                            {metric.description}
                                        </Paragraph>
                                    </Card>
                                </Col>
                            );
                        })}
                    </Row>
                </div>

                {/* Arena Leaderboard */}
                <Card
                    bordered={false}
                    style={{
                        borderRadius: 16,
                        background: '#141414',
                        border: '1px solid rgba(255,255,255,0.05)',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
                    }}
                    bodyStyle={{ padding: '24px 0' }}
                >
                    <div style={{ padding: '0 24px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Title level={4} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
                                <TrophyOutlined style={{ color: '#faad14' }} /> Model Arena 性能榜
                            </Title>
                            <Text type="secondary" style={{ fontSize: 12 }}>基于生产环境多维数据集的真实反馈结果。</Text>
                        </div>
                    </div>
                    <Table
                        dataSource={lb}
                        columns={arenaColumns}
                        rowKey="model"
                        pagination={false}
                        loading={loading}
                        className="premium-table"
                        style={{ background: 'transparent' }}
                    />
                </Card>

                {/* Methodology Highlight */}
                <Card size="small" style={{ borderRadius: 12, background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.1)' }}>
                    <Flex align="flex-start" gap={12}>
                        <SafetyCertificateOutlined style={{ color: '#52c41a', fontSize: 18, marginTop: 4 }} />
                        <div>
                            <Text strong style={{ display: 'block', marginBottom: 4 }}>评估方法论 (Methodology)</Text>
                            <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.6 }}>
                                本系统深度集成 <strong>RAGAS</strong> (Shahul Es et al., 2023) 开源评估框架。
                                系统从知识库自动抽取语料并交由参考模型生成 Ground Truth，通过独立的 Judge LLM 模拟专家评审，对生成结果实现毫秒级量化。
                                低分 Case 自动沉淀至 Bad Case 列表供专家复核，形成全链路反馈闭环。
                            </Text>
                        </div>
                    </Flex>
                </Card>
            </Space>
        );
    };

    return (
        <PageContainer
            title="多模型协同与评估 (M2.5)"
            description="基于 RAGAS 评估框架，对比不同大模型在特定知识库上的 Faithfulness / Relevance / Precision / Recall 指标，挑选最优生产方案。"
            actions={
                <Space size="middle">
                    <Button
                        type="default"
                        icon={<DownloadOutlined />}
                        onClick={handleExportReport}
                        disabled={reports.length === 0}
                        style={{ borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                    >
                        导出报告
                    </Button>
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setIsModalOpen(true)}
                        style={{ borderRadius: 8, height: 36, display: 'flex', alignItems: 'center' }}
                    >
                        生成测试集
                    </Button>
                </Space>
            }
        >
            <Tabs defaultActiveKey="arena" type="card">
                <TabPane tab={<span><TrophyOutlined /> Model Arena (排行榜)</span>} key="arena">
                    {renderRagasBenchmark()}
                </TabPane>

                <TabPane tab={<span><LineChartOutlined /> 评估报告 (Reports)</span>} key="reports">
                    <Table
                        dataSource={reports}
                        columns={reportColumns}
                        rowKey="id"
                        loading={loading}
                        pagination={{ pageSize: 10 }}
                    />
                </TabPane>

                <TabPane tab={<span><DatabaseOutlined /> 测试集管理 (Testsets)</span>} key="sets">
                    <Table
                        dataSource={sets}
                        columns={setColumns}
                        rowKey="id"
                        loading={loading}
                    />
                </TabPane>

                <TabPane tab={<span><BugOutlined /> Bad Cases</span>} key="badcases">
                    <Table
                        dataSource={badCases}
                        rowKey="id"
                        columns={[
                            { title: '时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
                            { title: '问题', dataIndex: 'question' },
                            { title: '差评答案', dataIndex: 'bad_answer', ellipsis: true },
                            { title: '原因', dataIndex: 'reason' },
                            { title: '状态', dataIndex: 'status', render: (s) => <Tag color="warning">{s.toUpperCase()}</Tag> }
                        ]}
                    />
                </TabPane>
            </Tabs>

            <Modal
                title="选择评估模型"
                open={isRunModalOpen}
                onCancel={() => setIsRunModalOpen(false)}
                onOk={() => runForm.submit()}
            >
                <Form form={runForm} layout="vertical" onFinish={confirmRunEval} initialValues={{ model_name: 'gpt-3.5-turbo' }}>
                    <Form.Item name="model_name" label="目标模型" rules={[{ required: true }]}>
                        <Select>
                            <Select.Option value="gpt-3.5-turbo">GPT-3.5 Turbo (Standard)</Select.Option>
                            <Select.Option value="gpt-4-turbo">GPT-4 Turbo (High Quality)</Select.Option>
                            <Select.Option value="claude-3-opus">Claude 3 Opus</Select.Option>
                            <Select.Option value="llama-3-8b">Llama-3-8B (Efficient)</Select.Option>
                            <Select.Option value="deepseek-chat">DeepSeek Chat (Cost Effective)</Select.Option>
                        </Select>
                    </Form.Item>
                    <Text type="secondary" style={{ fontSize: '12px' }}>系统将使用此模型生成回答，并由 Judge 模型进行客观评分。</Text>
                </Form>
            </Modal>

            <Modal
                title="生成 ground-truth 测试集"
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                onOk={() => form.submit()}
                confirmLoading={loading}
            >
                <Form form={form} layout="vertical" onFinish={handleCreateSet} initialValues={{ count: 10 }}>
                    <Form.Item name="name" label="测试集名称" rules={[{ required: true }]}>
                        <Input placeholder="例如: 核心文档评估" />
                    </Form.Item>
                    <Form.Item name="kb_id" label="目标知识库" rules={[{ required: true }]}>
                        <Select placeholder="请选择知识库">
                            {kbs.map(kb => <Select.Option key={kb.id} value={kb.id}>{kb.name}</Select.Option>)}
                        </Select>
                    </Form.Item>
                    <Form.Item name="count" label="样本数量" extra="数量越多评估越精准。">
                        <Select>
                            <Select.Option value={10}>10 对</Select.Option>
                            <Select.Option value={30}>30 对</Select.Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>

            <Modal
                title="评估明细报告"
                open={isDetailOpen}
                onCancel={() => setIsDetailOpen(false)}
                footer={null}
                width={850}
                styles={{ body: { maxHeight: '80vh', overflowY: 'auto' } }}
            >
                {renderDetails()}
            </Modal>
        </PageContainer>
    );
};
