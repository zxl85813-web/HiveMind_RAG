import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Space, Card, Progress, App, Modal, Form, Input, Select, Tabs, Statistic, Row, Col, Flex, Typography, theme, Alert, Checkbox, List, Popover, Switch } from 'antd';
import { BugOutlined, LineChartOutlined, DatabaseOutlined, PlayCircleOutlined, PlusOutlined, FileSearchOutlined, TrophyOutlined, ThunderboltOutlined, DollarOutlined, DownloadOutlined, ExperimentOutlined, SafetyCertificateOutlined, AimOutlined, CheckCircleOutlined, BulbOutlined, HistoryOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { PermissionButton } from '../components/common';
import { evalApi } from '../services/evalApi';
import { knowledgeApi } from '../services/knowledgeApi';
import type { EvaluationSet, EvaluationReport, KnowledgeBase } from '../types';
import { useAuthStore } from '../stores/authStore';
import { useMonitor } from '../hooks/useMonitor';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';

const { TabPane } = Tabs;
const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;

// ============================================================
//  RAGAS Benchmark Metric Definitions
// ============================================================
const RAGAS_METRICS = [
    {
        key: 'faithfulness',
        name: 'Faithfulness (忠实度)',
        icon: <SafetyCertificateOutlined />,
        color: 'var(--hm-color-success)',
        description: '衡量 AI 回答是否完全基于检索到的上下文，不产生幻觉 (Claim-level NLI)。',
        formula: 'Faithful Claims / Total Claims',
        benchmark: { excellent: 0.9, good: 0.7, poor: 0.5 }
    },
    {
        key: 'answer_relevance',
        name: 'Answer Relevance (答案相关性)',
        icon: <AimOutlined />,
        color: 'var(--hm-color-info)',
        description: '评估 AI 回答与用户问题的相关程度，从多角度检测偏题。',
        formula: 'Mean Cosine Sim(Generated Q, Original Q)',
        benchmark: { excellent: 0.9, good: 0.7, poor: 0.5 }
    },
    {
        key: 'instruction_following',
        name: 'Instruction Following (指令遵循)',
        icon: <ThunderboltOutlined />,
        color: 'var(--hm-color-warning)',
        description: '检查 AI 是否遵循了格式、风格或特定约束要求。',
        formula: 'Followed Instructions / Total Instructions',
        benchmark: { excellent: 1.0, good: 0.8, poor: 0.6 }
    },
    {
        key: 'hit_rate',
        name: 'Hit Rate (命中率)',
        icon: <CheckCircleOutlined />,
        color: 'hsl(180, 100%, 40%)',
        description: '评估 Top-K 检索结果中是否包含至少一个正确文档。',
        formula: 'Exists(Relevant Doc in Top-K)',
        benchmark: { excellent: 0.95, good: 0.8, poor: 0.6 }
    },
    {
        key: 'mrr',
        name: 'MRR (平均倒数排名)',
        icon: <LineChartOutlined />,
        color: 'hsl(265, 60%, 60%)',
        description: '衡量检索系统将相关文档排在首位的平均能力。',
        formula: 'Mean(1 / First_Relevant_Rank)',
        benchmark: { excellent: 0.8, good: 0.6, poor: 0.4 }
    },
    {
        key: 'ndcg',
        name: 'NDCG (归一化折损收益)',
        icon: <DatabaseOutlined />,
        color: 'hsl(330, 80%, 60%)',
        description: '全面衡量检索系统的排序质量，对高位排名的权重更敏感。',
        formula: 'DCG / IDCG',
        benchmark: { excellent: 0.85, good: 0.65, poor: 0.5 }
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
            <td style="text-align:center;">${(m.instruction_following || 0).toFixed(3)}</td>
            <td style="text-align:center;">${(m.hit_rate || 0).toFixed(3)}</td>
            <td style="text-align:center;">${(m.ndcg || 0).toFixed(3)}</td>
            <td style="text-align:center;">${Math.round(m.avgLatency)}ms</td>
            <td style="text-align:center;">$${m.avgCost.toFixed(4)}</td>
        </tr>
    `).join('');

    // Build per-report detail table
    const reportRows = completedReports.map(r => `
        <tr>
            <td>${new Date(r.created_at).toLocaleString()}</td>
            <td><code>${r.model_name}</code></td>
            <td style="text-align:center;">${(r.total_score * 100).toFixed(1)}%</td>
            <td style="text-align:center;">${r.faithfulness.toFixed(3)}</td>
            <td style="text-align:center;">${(r.instruction_following || 0).toFixed(3)}</td>
            <td style="text-align:center;">${(r.hit_rate || 0).toFixed(3)}</td>
            <td style="text-align:center;">${(r.mrr || 0).toFixed(3)}</td>
            <td style="text-align:center;">${Math.round(r.latency_ms)}ms</td>
            <td style="text-align:center;">$${(r.cost || 0).toFixed(4)}</td>
        </tr>
    `).join('');

    // Build Bad Cases section
    const badCaseRows = badCases.map(bc => `
        <tr>
            <td>${bc.question}</td>
            <td style="color:rgb(255,77,79);">${bc.bad_answer}</td>
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
                        <td style="text-align:center;color:${d.faithfulness > 0.7 ? 'rgb(82,196,26)' : 'rgb(255,77,79)'}">${d.faithfulness.toFixed(2)}</td>
                        <td style="text-align:center;color:${(d.instruction_following || 0) > 0.7 ? 'rgb(82,196,26)' : 'rgb(255,77,79)'}">${(d.instruction_following || 0).toFixed(2)}</td>
                    </tr>
                `).join('');
                qaDetail = `
                    <h2>📋 最优模型 QA 逐题分析 — ${bestModel}</h2>
                    <table>
                        <thead><tr>
                            <th>#</th><th>问题 (Question)</th><th>标准答案 (Ground Truth)</th><th>AI 回答</th><th>Faithfulness</th><th>Instruction</th>
                        </tr></thead>
                        <tbody>${qaRows}</tbody>
                    </table>
                `;
            } catch { /* ignore */ }
        }
    }

    // Score level
    const scoreLevel = avgScore > 0.8 ? '优秀 (Excellent)' : avgScore > 0.6 ? '良好 (Good)' : avgScore > 0.4 ? '待改进 (Needs Improvement)' : '不合格 (Poor)';
    const scoreBadge = avgScore > 0.8 ? 'rgb(82,196,26)' : avgScore > 0.6 ? 'rgb(24,144,255)' : avgScore > 0.4 ? 'rgb(250,173,20)' : 'rgb(255,77,79)';

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HiveMind RAG 评估综合报告</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', sans-serif; background: rgb(13,17,23); color: rgb(201,209,217); padding: 40px; line-height: 1.7; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 40px; padding: 40px; background: linear-gradient(135deg, rgb(22,27,34) 0%, rgb(26,35,50) 100%); border-radius: 16px; border: 1px solid rgba(48,54,61,0.8); }
        .header h1 { font-size: 28px; color: rgb(88,166,255); margin-bottom: 8px; }
        .header .subtitle { color: rgb(139,148,158); font-size: 14px; }
        .header .score-badge { display: inline-block; margin-top: 16px; padding: 8px 24px; border-radius: 20px; font-size: 20px; font-weight: bold; color: white; }
        h2 { color: rgb(88,166,255); font-size: 20px; margin: 36px 0 16px; padding-bottom: 8px; border-bottom: 1px solid rgb(33,38,45); }
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
        .metric-card { background: rgb(22,27,34); border: 1px solid rgb(48,54,61); border-radius: 12px; padding: 20px; text-align: center; }
        .metric-card .value { font-size: 28px; font-weight: bold; color: rgb(88,166,255); }
        .metric-card .label { font-size: 12px; color: rgb(139,148,158); margin-top: 4px; }
        .ragas-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
        .ragas-card { background: rgb(22,27,34); border: 1px solid rgb(48,54,61); border-radius: 12px; padding: 20px; }
        .ragas-card .metric-name { font-size: 15px; font-weight: bold; margin-bottom: 6px; }
        .ragas-card .metric-desc { font-size: 12px; color: rgb(139,148,158); margin-bottom: 10px; }
        .ragas-card .metric-formula { font-family: 'Courier New', monospace; font-size: 11px; color: rgb(121,192,255); background: rgb(13,17,23); padding: 4px 8px; border-radius: 4px; display: inline-block; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 24px; background: rgb(22,27,34); border-radius: 8px; overflow: hidden; }
        th { background: rgb(33,38,45); color: rgb(201,209,217); padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; }
        td { padding: 10px 16px; border-bottom: 1px solid rgb(33,38,45); font-size: 13px; }
        tr:last-child td { border-bottom: none; }
        code { background: rgb(31,41,55); padding: 2px 6px; border-radius: 4px; font-size: 12px; color: rgb(121,192,255); }
        .badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .badge-success { background: rgba(82,196,26,0.2); color: rgb(82,196,26); }
        .badge-warning { background: rgba(250,173,20,0.2); color: rgb(250,173,20); }
        .badge-danger { background: rgba(255,77,79,0.2); color: rgb(255,77,79); }
        .footer { text-align: center; margin-top: 48px; padding: 24px; color: rgb(72,79,88); font-size: 12px; border-top: 1px solid rgb(33,38,45); }
        @media print { body { background: white; color: rgb(31,35,40); } .header { background: rgb(246,248,250); } h2 { color: rgb(9,105,218); } table, .metric-card, .ragas-card { background: rgb(246,248,250); border-color: rgb(208,215,222); } th { background: rgb(238,238,238); color: rgb(51,51,51); } td { border-color: rgb(208,215,222); color: rgb(31,35,40); } .footer { color: rgb(153,153,153); } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🧠 HiveMind RAG 评估综合报告</h1>
        <div class="subtitle">基于多维原子指标 (MRR, NDCG, NLI-Faithfulness) 的全面质量评估</div>
        <div class="subtitle" style="margin-top:4px;">报告生成时间: ${exportTime}</div>
        <div class="score-badge" style="background:${scoreBadge}">综合评级: ${scoreLevel} - ${(avgScore * 100).toFixed(1)}%</div>
    </div>

    <h2>📊 评估概览 (Executive Summary)</h2>
    <div class="metrics-grid">
        <div class="metric-card"><div class="value">${totalEvals}</div><div class="label">评测总次数</div></div>
        <div class="metric-card"><div class="value">${(avgScore * 100).toFixed(1)}%</div><div class="label">平均综合得分</div></div>
        <div class="metric-card"><div class="value">${Math.round(avgLatency)}ms</div><div class="label">平均响应延迟</div></div>
        <div class="metric-card"><div class="value">$${totalCost.toFixed(4)}</div><div class="label">累计评估成本</div></div>
    </div>

    <h2>🔬 RAG 高阶评估指标体系</h2>
    <div class="ragas-grid">
        <div class="ragas-card">
            <div class="metric-name" style="color:rgb(82,196,26)">✅ Faithfulness (忠实度)</div>
            <div class="metric-desc">衡量 AI 回答是否完全基于检索到的上下文，不产生幻觉 (Claim-level NLI)。</div>
            <div class="metric-formula">Score = Faithful Claims / Total Claims</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:rgb(24,144,255)">🎯 Answer Relevance (答案相关性)</div>
            <div class="metric-desc">评估 AI 回答与用户问题的相关程度。</div>
            <div class="metric-formula">Score = Mean Cosine Sim(Generated Q, Original Q)</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:rgb(250,173,20)">⚡ Instruction Following (指令遵循)</div>
            <div class="metric-desc">检查 AI 是否遵循了格式、风格或特定约束要求。</div>
            <div class="metric-formula">Score = Followed Instructions / Total Instructions</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:rgb(0,255,255)">🔍 Hit Rate (命中率)</div>
            <div class="metric-desc">Top-K 结果中包含正确片段的概率。</div>
            <div class="metric-formula">Score = Binary Hit in Top-K</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:rgb(180,100,255)">📈 MRR (平均倒数排名)</div>
            <div class="metric-desc">衡量检索结果排位的平均倒数。</div>
            <div class="metric-formula">Score = Mean(1 / Rank)</div>
        </div>
        <div class="ragas-card">
            <div class="metric-name" style="color:rgb(255,100,200)">💎 NDCG (归一化折损收益)</div>
            <div class="metric-desc">衡量检索系统的多级排序质量。</div>
            <div class="metric-formula">Score = DCG / IDCG</div>
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
        <div class="metric-name" style="color:rgb(88,166,255);">RAGAS (Retrieval Augmented Generation Assessment)</div>
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
    const { track } = useMonitor();

    React.useEffect(() => {
        track('system', 'page_load', { page: 'EvaluationDashboard' });
    }, [track]);
    
    const { message } = App.useApp();
    const { token } = theme.useToken();
    const hasAccess = useAuthStore((state) => state.hasAccess);
    const [sets, setSets] = useState<EvaluationSet[]>([]);
    const [reports, setReports] = useState<EvaluationReport[]>([]);
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [badCases, setBadCases] = useState<any[]>([]);
    const [directives, setDirectives] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [form] = Form.useForm();
    const [runForm] = Form.useForm();
    const [selectedReport, setSelectedReport] = useState<EvaluationReport | null>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isRunModalOpen, setIsRunModalOpen] = useState(false);
    const [activeSetId, setActiveSetId] = useState<string | null>(null);
    const [isSMEModalOpen, setIsSMEModalOpen] = useState(false);
    const [smeForm] = Form.useForm();
    const [smeContext, setSmeContext] = useState("");
    const [smeClaims, setSmeClaims] = useState<string[]>([]);
    const [smeConsistency, setSmeConsistency] = useState<{ is_consistent: boolean, issues: string[] } | null>(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [setsRes, reportsRes, kbsRes, badCasesRes, directivesRes] = await Promise.all([
                evalApi.getTestsets(),
                evalApi.getReports(),
                knowledgeApi.listKBs(),
                evalApi.getBadCases(),
                evalApi.getDirectives()
            ]);
            setSets(setsRes.data.data || []);
            setReports(reportsRes.data.data || []);
            setKbs(kbsRes.data.data || []);
            setBadCases(badCasesRes.data.data || []);
            setDirectives(directivesRes.data.data || []);
        } catch {
            message.error("数据加载失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleCreateSet = async (values: any) => {
        if (!hasAccess({ anyPermissions: ['evaluation:run'] })) {
            message.warning('当前账号没有创建评测集权限');
            return;
        }

        try {
            await evalApi.createTestset(values.kb_id, values.name, values.count);
            message.success("测试集生成任务已启动，请稍后刷新查看");
            setIsModalOpen(false);
            form.resetFields();
            fetchData(); // Refresh to catch potential updates
        } catch {
            message.error("创建失败");
        }
    };

    const handleRunEval = (setId: string) => {
        if (!hasAccess({ anyPermissions: ['evaluation:run'] })) {
            message.warning('当前账号没有运行评测权限');
            return;
        }
        setActiveSetId(setId);
        setIsRunModalOpen(true);
    };

    const confirmRunEval = async (values: any) => {
        if (!activeSetId) return;
        if (!hasAccess({ anyPermissions: ['evaluation:run'] })) {
            message.warning('当前账号没有运行评测权限');
            return;
        }
        try {
            await evalApi.runEvaluation(activeSetId, values.model_name, values.apply_reflection);
            message.success(`针对模型 ${values.model_name} 的评估任务已启动 (鲁棒模式: ${values.apply_reflection ? '开启' : '关闭'})`);
            setIsRunModalOpen(false);
        } catch {
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
            modelStats[m].instruction_following = (modelStats[m].instruction_following || 0) + (r.instruction_following || 0);
            modelStats[m].mrr = (modelStats[m].mrr || 0) + (r.mrr || 0);
            modelStats[m].hit_rate = (modelStats[m].hit_rate || 0) + (r.hit_rate || 0);
            modelStats[m].ndcg = (modelStats[m].ndcg || 0) + (r.ndcg || 0);
            modelStats[m].count += 1;
        });

        return Object.values(modelStats).map((s: any) => ({
            ...s,
            avgScore: s.avgScore / s.count,
            avgLatency: s.avgLatency / s.count,
            avgCost: s.avgCost / s.count,
            faithfulness: s.faithfulness / s.count,
            relevance: s.relevance / s.count,
            instruction_following: s.instruction_following / s.count,
            mrr: s.mrr / s.count,
            hit_rate: s.hit_rate / s.count,
            ndcg: s.ndcg / s.count
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
                <PermissionButton
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    size="small"
                    onClick={() => handleRunEval(record.id)}
                    access={{ anyPermissions: ['evaluation:run'] }}
                >
                    运行评估
                </PermissionButton>
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
                    strokeColor={score > 0.7 ? token.colorSuccess : score > 0.4 ? token.colorWarning : token.colorError}
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
            render: (s: number) => <Progress percent={Math.round(s * 100)} strokeColor={token.colorInfo} />
        },
        {
            title: 'Instruction Following',
            dataIndex: 'instruction_following',
            key: 'inst',
            render: (s: number) => <Tag color="orange">{(s || 0).toFixed(2)}</Tag>
        },
        {
            title: 'Hit Rate',
            dataIndex: 'hit_rate',
            key: 'hr',
            render: (s: number) => <Tag color="cyan">{(s || 0).toFixed(2)}</Tag>
        },
        {
            title: 'MRR / NDCG',
            key: 'retrieval',
            render: (_: any, record: any) => (
                <Space direction="vertical" size={0}>
                    <Text size="small" type="secondary">MRR: {(record.mrr || 0).toFixed(2)}</Text>
                    <Text size="small" type="secondary">NDCG: {(record.ndcg || 0).toFixed(2)}</Text>
                </Space>
            )
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
        } catch { /* ignore */ }

        return (
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Card size="small" style={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', backdropFilter: 'blur(10px)' }}>
                    <Row gutter={16}>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>模型</span>} value={selectedReport.model_name} valueStyle={{ fontSize: 14, color: token.colorText }} /></Col>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>延迟</span>} value={selectedReport.latency_ms} suffix={<span style={{ fontSize: 12 }}>ms</span>} valueStyle={{ fontSize: 14, color: token.colorText }} /></Col>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>成本</span>} value={selectedReport.cost} prefix="$" precision={4} valueStyle={{ fontSize: 14, color: token.colorWarning }} /></Col>
                        <Col span={6}><Statistic title={<span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>Token</span>} value={selectedReport.token_usage || 0} valueStyle={{ fontSize: 14, color: token.colorText }} /></Col>
                    </Row>
                </Card>

                {/* RAGAS Metrics Summary for this report */}
                <Card size="small" style={{ borderRadius: 12, background: 'rgba(20,20,20,0.4)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <Row gutter={[16, 16]}>
                        <Col span={4}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Faithfulness</span>} value={selectedReport.faithfulness} precision={3}
                                valueStyle={{ fontSize: 14, color: selectedReport.faithfulness > 0.7 ? token.colorSuccess : token.colorWarning }} />
                        </Col>
                        <Col span={4}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Relevance</span>} value={selectedReport.answer_relevance} precision={3}
                                valueStyle={{ fontSize: 14, color: selectedReport.answer_relevance > 0.7 ? token.colorSuccess : token.colorWarning }} />
                        </Col>
                        <Col span={4}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Instruction</span>} value={selectedReport.instruction_following || 0} precision={3}
                                valueStyle={{ fontSize: 14, color: (selectedReport.instruction_following || 0) > 0.7 ? token.colorSuccess : token.colorWarning }} />
                        </Col>
                        <Col span={4}>
                            <Statistic title={<span style={{ fontSize: 11 }}>Hit Rate</span>} value={selectedReport.hit_rate || 0} precision={3}
                                valueStyle={{ fontSize: 14, color: (selectedReport.hit_rate || 0) > 0.8 ? token.colorSuccess : token.colorWarning }} />
                        </Col>
                        <Col span={4}>
                            <Statistic title={<span style={{ fontSize: 11 }}>MRR</span>} value={selectedReport.mrr || 0} precision={3}
                                valueStyle={{ fontSize: 14, color: (selectedReport.mrr || 0) > 0.6 ? token.colorSuccess : token.colorWarning }} />
                        </Col>
                        <Col span={4}>
                            <Statistic title={<span style={{ fontSize: 11 }}>NDCG</span>} value={selectedReport.ndcg || 0} precision={3}
                                valueStyle={{ fontSize: 14, color: (selectedReport.ndcg || 0) > 0.6 ? token.colorSuccess : token.colorWarning }} />
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
                                    <Tag color={item.faithfulness > 0.7 ? 'success' : 'error'} bordered={false} style={{ fontSize: 10 }}>F: {item.faithfulness.toFixed(2)}</Tag>
                                    <Tag color={item.answer_correctness > 0.7 ? 'success' : 'error'} bordered={false} style={{ fontSize: 10 }}>A: {(item.answer_correctness || 0).toFixed(2)}</Tag>
                                </Space>
                            }
                        >
                            <div style={{ marginBottom: 12 }}>
                                <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>Q</Text>
                                <Text strong>{item.question}</Text>
                            </div>
                            <div style={{ marginBottom: 12, padding: '10px 14px', background: 'rgba(24,144,255,0.05)', borderRadius: 8, border: '1px solid rgba(24,144,255,0.1)' }}>
                                <Text style={{ fontSize: 11, color: token.colorInfo, display: 'block', marginBottom: 4 }}>Standard Answer</Text>
                                <Text style={{ fontSize: 13, opacity: 0.85 }}>{item.ground_truth}</Text>
                            </div>
                            <div style={{ marginBottom: 12, padding: '10px 14px', background: 'rgba(82,196,26,0.05)', borderRadius: 8, border: '1px solid rgba(82,196,26,0.1)' }}>
                                <Text style={{ fontSize: 11, color: token.colorSuccess, display: 'block', marginBottom: 4 }}>Model Generated</Text>
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
            instruction_following: completedReports.length > 0 ? completedReports.reduce((s, r) => s + (r.instruction_following || 0), 0) / completedReports.length : 0,
            mrr: completedReports.length > 0 ? completedReports.reduce((s, r) => s + (r.mrr || 0), 0) / completedReports.length : 0,
            hit_rate: completedReports.length > 0 ? completedReports.reduce((s, r) => s + (r.hit_rate || 0), 0) / completedReports.length : 0,
            ndcg: completedReports.length > 0 ? completedReports.reduce((s, r) => s + (r.ndcg || 0), 0) / completedReports.length : 0,
        };

        const metricColors = {
            faithfulness: 'hsl(145, 63%, 49%)',
            answer_relevance: 'hsl(210, 100%, 60%)',
            instruction_following: 'hsl(38, 100%, 50%)',
            hit_rate: 'hsl(180, 100%, 40%)',
            mrr: 'hsl(265, 60%, 60%)',
            ndcg: 'hsl(330, 80%, 60%)'
        };

        return (
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                {/* RAGAS Metrics Overview - Bento/Card Style */}
                <div>
                    <Flex align="center" gap={8} style={{ marginBottom: 16 }}>
                        <ExperimentOutlined style={{ color: token.colorInfo, fontSize: 18 }} />
                        <Title level={5} style={{ margin: 0, fontWeight: 500 }}>RAGAS 综合质量看板</Title>
                    </Flex>
                    <Row gutter={[12, 12]}>
                        {RAGAS_METRICS.map(metric => {
                             const val = (avgMetrics as any)[metric.key] || 0;
                             const bm = metric.benchmark;
                             const level = val >= bm.excellent ? 'Excellent' : val >= bm.good ? 'Good' : val >= bm.poor ? 'Fair' : 'Poor';
                             const baseColor = (metricColors as any)[metric.key];

                             return (
                                 <Col span={4} key={metric.key}>
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
                                                <Title level={3} style={{ margin: 0, color: token.colorText, fontWeight: 600 }}>{Math.round(val * 100)}<span style={{ fontSize: 14, opacity: 0.45 }}>%</span></Title>
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
                        background: token.colorBgContainer,
                        border: '1px solid rgba(255,255,255,0.05)',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
                    }}
                    bodyStyle={{ padding: '24px 0' }}
                >
                    <div style={{ padding: '0 24px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Title level={4} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
                                <TrophyOutlined style={{ color: token.colorWarning }} /> Model Arena 性能榜
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
                        <SafetyCertificateOutlined style={{ color: token.colorSuccess, fontSize: 18, marginTop: 4 }} />
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

    const renderTrendChart = () => {
        const completed = reports
            .filter(r => r.status === 'completed')
            .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

        if (completed.length < 2) {
            return (
                <Card style={{ borderRadius: 16, background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.1)', padding: 40, textAlign: 'center', marginTop: 20 }}>
                    <LineChartOutlined style={{ fontSize: 48, color: 'rgba(255,255,255,0.1)', marginBottom: 16 }} />
                    <Text type="secondary" style={{ display: 'block' }}>需要至少 2 条已完成的报告来生成趋势分析 (Needs at least 2 reports)</Text>
                </Card>
            );
        }

        const data = completed.map(r => ({
            time: new Date(r.created_at).toLocaleDateString() + ' ' + new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            faithfulness: r.faithfulness,
            relevance: r.answer_relevance,
            instruction: r.instruction_following || 0,
            hit_rate: r.hit_rate || 0,
            full: r.total_score,
            model: r.model_name
        }));

        return (
            <Space direction="vertical" style={{ width: '100%' }} size="large" className="trend-container">
                <Card 
                    title={<span style={{ fontWeight: 600 }}><LineChartOutlined /> 质量演进趋势 (RAGAS Quality Evolution)</span>}
                    bordered={false}
                    style={{ borderRadius: 16, background: token.colorBgContainer, border: '1px solid rgba(255,255,255,0.05)', boxShadow: '0 8px 32px rgba(0,0,0,0.2)', marginTop: 20 }}
                >
                    <div style={{ height: 400, width: '100%', marginTop: 20 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis 
                                    dataKey="time" 
                                    stroke="rgba(255,255,255,0.45)" 
                                    fontSize={10} 
                                    tick={{ fill: 'rgba(255,255,255,0.45)' }}
                                    axisLine={false}
                                />
                                <YAxis 
                                    stroke="rgba(255,255,255,0.45)" 
                                    fontSize={10} 
                                    domain={[0, 1]}
                                    tick={{ fill: 'rgba(255,255,255,0.45)' }}
                                    axisLine={false}
                                />
                                <RechartsTooltip 
                                    contentStyle={{ background: '#1c1c1e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}
                                    itemStyle={{ fontSize: 12, fontWeight: 500 }}
                                />
                                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: 12, opacity: 0.8 }} />
                                <ReferenceLine y={0.7} label={{ value: "Stability Gate", position: 'insideBottomRight', fill: '#EF476F', fontSize: 10 }} stroke="#EF476F" strokeDasharray="3 3" />
                                
                                <Line type="monotone" dataKey="faithfulness" name="Faithfulness" stroke="hsl(145, 63%, 49%)" strokeWidth={3} dot={{ r: 4, strokeWidth: 2, fill: '#000' }} activeDot={{ r: 6 }} />
                                <Line type="monotone" dataKey="relevance" name="Relevance" stroke="hsl(210, 100%, 60%)" strokeWidth={3} dot={{ r: 4, strokeWidth: 2, fill: '#000' }} />
                                <Line type="monotone" dataKey="instruction" name="Instruction" stroke="hsl(38, 100%, 50%)" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                                <Line type="monotone" dataKey="hit_rate" name="Hit Rate" stroke="hsl(180, 100%, 40%)" strokeWidth={2} dot={{ r: 3 }} />
                                <Line type="monotone" dataKey="full" name="Composite Score" stroke="#fff" strokeWidth={4} dot={{ r: 6, fill: '#fff', strokeWidth: 0 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </Card>

                <Alert 
                    message={<Text strong style={{ color: token.colorInfo }}>🧠 智体自省 (Agent Observation)</Text>}
                    description={
                        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
                            Composite Score (白线) 是系统的核心北极星指标。
                            若观察到 <strong>Faithfulness</strong> 下滑，通常意味着检索上下文包含过多干扰噪声；
                            若 <strong>Hit Rate</strong> 较低，建议优化 Rerank 模型或增加 Top-K 值。
                            当前的稳定性门禁线设为 0.7，持续低于该值将触发架构重构建议。
                        </div>
                    }
                    type="info"
                    showIcon
                    style={{ borderRadius: 16, background: 'rgba(24,144,255,0.05)', border: '1px solid rgba(24,144,255,0.1)' }}
                />
            </Space>
        );
    };

    const tabItems = [
        {
            key: 'arena',
            label: <span><TrophyOutlined /> Model Arena (排行榜)</span>,
            children: renderRagasBenchmark()
        },
        {
            key: 'trend',
            label: <span><LineChartOutlined /> 质量趋势 (Trends)</span>,
            children: renderTrendChart()
        },
        {
            key: 'reports',
            label: <span><HistoryOutlined /> 评估报告 (Reports)</span>,
            children: (
                <Table
                    dataSource={reports}
                    columns={reportColumns}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            )
        },
        {
            key: 'sets',
            label: <span><DatabaseOutlined /> 测试集管理 (Testsets)</span>,
            children: (
                <Table
                    dataSource={sets}
                    columns={setColumns}
                    rowKey="id"
                    loading={loading}
                />
            )
        },
        {
            key: 'badcases',
            label: <span><BugOutlined /> Bad Cases (待校对)</span>,
            children: (
                <Table
                    dataSource={badCases}
                    rowKey="id"
                    columns={[
                        { title: '时间', dataIndex: 'created_at', width: 140, render: (t: string) => new Date(t).toLocaleString() },
                        { title: '问题', dataIndex: 'question', width: 250 },
                        { title: 'AI 答案', dataIndex: 'bad_answer', ellipsis: true },
                        { 
                            title: '标准答案 (Human)', 
                            dataIndex: 'expected_answer', 
                            render: (v: string, record: any) => (
                                <Input 
                                    defaultValue={v} 
                                    placeholder="点击输入正确答案..."
                                    onBlur={(e) => {
                                        if (e.target.value !== v) {
                                            evalApi.updateBadCase(record.id, record.status, e.target.value).then(() => {
                                                message.success("已记录人工修正");
                                                fetchData();
                                            });
                                        }
                                    }}
                                />
                            )
                        },
                        { title: '状态', dataIndex: 'status', width: 120, render: (s: string) => <Tag color={s === 'added_to_dataset' ? 'success' : 'warning'}>{s.toUpperCase()}</Tag> },
                        { 
                            title: '系统诊断 (AI Insight)', 
                            dataIndex: 'ai_insight', 
                            width: 200,
                            render: (v: string) => <Text type="secondary" size="small" italic>{v || '无诊断建议'}</Text>
                        },
                        {
                            title: '协作进化',
                            key: 'evolve',
                            width: 150,
                            render: (_: any, record: any) => (
                                <Space>
                                    <Popover 
                                        title="证据溯源 (Context Snapshot)" 
                                        content={<div style={{ maxWidth: 400, maxHeight: 300, overflowY: 'auto' }}><Text size="small">{record.context_snapshot || '未记录上下文'}</Text></div>}
                                    >
                                        <Button size="small" icon={<FileSearchOutlined />}>证据</Button>
                                    </Popover>
                                    <Button 
                                        type="primary" 
                                        size="small" 
                                        disabled={!record.expected_answer || record.status === 'added_to_dataset'}
                                        onClick={async () => {
                                            setLoading(true);
                                            try {
                                                await evalApi.promoteBadCase(record.id);
                                                message.success("✅ 已晋升为黄金标准并触发认知学习！");
                                                fetchData();
                                            } catch {
                                                message.error("晋升失败");
                                            } finally {
                                                setLoading(false);
                                            }
                                        }}
                                    >
                                        晋升
                                    </Button>
                                </Space>
                            )
                        }
                    ]}
                />
            )
        },
        {
            key: 'evolution',
            label: <span><ThunderboltOutlined /> 协同进化 (Cognitive Directives)</span>,
            children: (
                <div style={{ padding: '20px' }}>
                    <div style={{ marginBottom: '20px' }}>
                        <Title level={4}>🧠 集群认知指令集 (Evolution Results)</Title>
                        <Text type="secondary">基于人机协同纠错过程，系统自动提炼的“群体指令”。这些规则将强制注入后续所有 Agent 执行周期中。</Text>
                    </div>
                    <List
                        grid={{ gutter: 16, column: 2 }}
                        dataSource={directives}
                        renderItem={item => (
                            <List.Item>
                                <Card 
                                    title={<Tag color="purple">{item.topic}</Tag>}
                                    extra={<Text type="secondary">v{item.version}</Text>}
                                    style={{ borderLeft: '4px solid #722ed1', borderRadius: '8px' }}
                                >
                                    <Text strong style={{ fontSize: '15px' }}>{item.directive}</Text>
                                    <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between' }}>
                                        <Text size="small" type="secondary">信度: {(item.confidence_score * 100).toFixed(1)}%</Text>
                                        <Text size="small" type="secondary">更新: {new Date(item.updated_at).toLocaleDateString()}</Text>
                                    </div>
                                </Card>
                            </List.Item>
                        )}
                    />
                </div>
            )
        }
    ];

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
                        style={{ borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: token.colorText, border: '1px solid rgba(255,255,255,0.1)' }}
                    >
                        导出报告
                    </Button>
                    <PermissionButton
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setIsModalOpen(true)}
                        access={{ anyPermissions: ['evaluation:run'] }}
                        style={{ borderRadius: 8, height: 36, display: 'flex', alignItems: 'center' }}
                    >
                        生成测试集
                    </PermissionButton>
                    <Button
                        type="primary"
                        icon={<BulbOutlined />}
                        onClick={() => setIsSMEModalOpen(true)}
                        style={{ background: '#722ed1', borderColor: '#722ed1' }}
                    >
                        专家辅助录入
                    </Button>
                </Space>
            }
        >
            <Tabs defaultActiveKey="arena" type="card" items={tabItems} />

            <Modal
                title="选择评估模型"
                open={isRunModalOpen}
                onCancel={() => setIsRunModalOpen(false)}
                onOk={() => runForm.submit()}
            >
                <Form form={runForm} layout="vertical" onFinish={confirmRunEval} initialValues={{ model_name: 'gpt-3.5-turbo', apply_reflection: false }}>
                    <Form.Item name="model_name" label="目标模型" rules={[{ required: true }]}>
                        <Select>
                            <Select.Option value="gpt-3.5-turbo">GPT-3.5 Turbo (Standard)</Select.Option>
                            <Select.Option value="gpt-4-turbo">GPT-4 Turbo (High Quality)</Select.Option>
                            <Select.Option value="claude-3-opus">Claude 3 Opus</Select.Option>
                            <Select.Option value="llama-3-8b">Llama-3-8B (Efficient)</Select.Option>
                            <Select.Option value="deepseek-chat">DeepSeek Chat (Cost Effective)</Select.Option>
                        </Select>
                    </Form.Item>
                    <Form.Item name="apply_reflection" label="智体自省 (鲁棒模式)" valuePropName="checked">
                        <Switch />
                    </Form.Item>
                    <Text type="secondary" style={{ fontSize: '11px', display: 'block', marginBottom: '16px' }}>
                        启用该选项后，Judge 模型将对评分结果进行自我审查（Self-Correction），有效降低“幻觉”和“倾向性偏差”，但评估耗时将翻倍。
                    </Text>
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
            <Modal
                title={<span><BulbOutlined /> 业务专家标注工作台 (SME Workspace)</span>}
                open={isSMEModalOpen}
                onCancel={() => setIsSMEModalOpen(false)}
                width={1000}
                footer={null}
            >
                <div style={{ display: 'flex', gap: '24px' }}>
                    <div style={{ flex: 1, background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <Title level={5}>📖 参考原文 (证据区)</Title>
                        <TextArea 
                            rows={15} 
                            placeholder="请粘贴文档原文段落到这里，AI将根据此段落辅助您校验..." 
                            value={smeContext}
                            onChange={(e) => setSmeContext(e.target.value)}
                            style={{ background: 'transparent' }}
                        />
                    </div>
                    <div style={{ flex: 1.2 }}>
                        <Form form={smeForm} layout="vertical">
                            <Form.Item label="1. 业务问题 (Question)" name="question" rules={[{ required: true }]}>
                                <Input.TextArea placeholder="模拟客户的真实提问..." />
                            </Form.Item>
                            
                            <Form.Item label="2. 标准正解 (Standard Answer)" name="answer" rules={[{ required: true }]}>
                                <Input.TextArea 
                                    rows={5} 
                                    placeholder="请输入这份文件的教科书式回答..." 
                                    onBlur={async (e) => {
                                        const text = e.target.value;
                                        if (!text || !smeContext) return;
                                        // Trigger Consistency Check
                                        const res = await evalApi.verifySMEAnswer(text, smeContext);
                                        setSmeConsistency(res.data.data);
                                    }}
                                />
                            </Form.Item>

                            {smeConsistency && !smeConsistency.is_consistent && (
                                <Alert 
                                    message="逻辑一致性红线预警" 
                                    description={smeConsistency.issues.join(', ')} 
                                    type="error" 
                                    showIcon 
                                    style={{ marginBottom: '16px' }}
                                />
                            )}

                            <Button 
                                type="dashed" 
                                block 
                                onClick={async () => {
                                    const answer = smeForm.getFieldValue('answer');
                                    if (!answer) return;
                                    setLoading(true);
                                    const res = await evalApi.assistClaims(answer);
                                    setSmeClaims(res.data.data);
                                    setLoading(false);
                                }}
                                style={{ marginBottom: '16px' }}
                            >
                                ✨ 自动拆解核心知识点 (Claim Decomposition)
                            </Button>

                            {smeClaims.length > 0 && (
                                <div style={{ marginBottom: '20px', padding: '12px', background: 'rgba(114, 46, 209, 0.05)', borderRadius: '8px' }}>
                                    <Text type="secondary" size="small">评测基准 Checklist:</Text>
                                    <div style={{ marginTop: '8px' }}>
                                        {smeClaims.map((c, i) => <Checkbox key={i} checked style={{ display: 'block', marginBottom: '4px' }}>{c}</Checkbox>)}
                                    </div>
                                </div>
                            )}

                            <div style={{ textAlign: 'right' }}>
                                <Button 
                                    type="primary" 
                                    size="large" 
                                    loading={loading}
                                    onClick={async () => {
                                        try {
                                            const values = await smeForm.validateFields();
                                            setLoading(true);
                                            await evalApi.submitSMEGoldCase(values.question, values.answer, smeContext);
                                            message.success("金色标准已入库，并自动对齐原子事实点！");
                                            setIsSMEModalOpen(false);
                                            smeForm.resetFields();
                                            setSmeClaims([]);
                                            setSmeContext("");
                                            setSmeConsistency(null);
                                            fetchData();
                                        } catch (err) {
                                            message.error("提交失败，请检查输入项");
                                        } finally {
                                            setLoading(false);
                                        }
                                    }}
                                >
                                    提交并入库 (Save to Gold Set)
                                </Button>
                            </div>
                        </Form>
                    </div>
                </div>
            </Modal>
        </PageContainer>
    );
};
