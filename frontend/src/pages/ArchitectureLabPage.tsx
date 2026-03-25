import React from 'react';
import { Card, Row, Col, Statistic, Typography, Divider, Badge, Empty, Spin, Button } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { 
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Legend
} from 'recharts';
import ReactMarkdown from 'react-markdown';
import { Zap, ShieldAlert, Cpu, RefreshCw } from 'lucide-react';
import api from '../services/api';

const { Title, Text, Paragraph } = Typography;

interface BaselineStats {
    count: number;
    mean: number;
    max: number;
}

interface BaselineData {
    [metricName: string]: {
        [groupName: string]: BaselineStats;
    };
}

interface DiagnosisResult {
    status: 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'INSUFFICIENT_DATA';
    metrics_snapshot: BaselineData;
    analysis: string;
}

const ArchitectureLabPage: React.FC = () => {
    // 1. 获取基线数据摘要
    const { data: report, isLoading: loadingReport, refetch: refetchReport } = useQuery({
        queryKey: ['baseline-overall-report'],
        queryFn: async () => {
            const res = await api.get('/observability/baseline-report');
            return res.data.data as BaselineData;
        }
    });

    // 2. 获取 AI 诊断报告
    const { data: diagnosis, isLoading: loadingDiagnosis, refetch: refetchDiagnosis } = useQuery({
        queryKey: ['baseline-ai-diagnosis'],
        queryFn: async () => {
            const res = await api.get('/observability/baseline/ai-diagnosis');
            return res.data.data as DiagnosisResult;
        },
        enabled: !!report && Object.keys(report).length > 0
    });

    // 3. 阶段审计 (Phase Gate Reflection)
    const { data: phaseAudit, isLoading: loadingAudit, refetch: refetchAudit } = useQuery({
        queryKey: ['hmer-phase-audit'],
        queryFn: async () => {
            const res = await api.get('/observability/baseline/phase-gate/0');
            return res.data.data as { audit_report: string; ready_to_proceed: boolean };
        },
        enabled: !!report
    });

    const handleRefresh = () => {
        refetchReport();
        refetchDiagnosis();
        refetchAudit();
    };

    // 转化 A/B 对比数据
    const chartData = report ? Object.entries(report).map(([name, groups]) => ({
        name: name.replace(' (Baseline)', ''),
        control: groups.control?.mean || 0,
        experiment: groups.experiment?.mean || 0,
        delta: groups.experiment && groups.control 
               ? ((groups.experiment.mean - groups.control.mean) / groups.control.mean * 100).toFixed(1)
               : null
    })) : [];

    return (
        <div style={{ padding: '24px', background: 'var(--ant-color-bg-layout)', minHeight: '100vh' }}>
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <Title level={2}>
                        <Cpu style={{ marginRight: 8, verticalAlign: 'bottom' }} size={28} />
                        AI 架构实验室 (Architecture Lab)
                    </Title>
                    <Text type="secondary">基于 HMER 体系的版本性能对比与架构反思</Text>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                    <Button 
                        onClick={() => {
                            localStorage.setItem('HMER_EXP_GROUP', 'experiment');
                            window.location.reload();
                        }}
                        danger={localStorage.getItem('HMER_EXP_GROUP') === 'experiment'}
                    >
                        切换至测试组 (Experiment)
                    </Button>
                    <Button 
                        type="primary" 
                        icon={<RefreshCw size={16} style={{ marginRight: 4 }} />} 
                        onClick={handleRefresh}
                        loading={loadingReport || loadingDiagnosis || loadingAudit}
                    >
                        执行阶段诊断
                    </Button>
                </div>
            </div>

            {/* 第一排：核心指标概览 (以 TTFT 为例) */}
            <Row gutter={16}>
                <Col span={8}>
                    <Card bordered={false}>
                        <Statistic
                            title="TTFT 平均延迟 (Control)"
                            value={report?.['TTFT (Baseline)']?.control?.mean || 0}
                            precision={1}
                            suffix="ms"
                            prefix={<Zap size={18} color="var(--ant-color-text-description)" />}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card bordered={false}>
                        <Statistic
                            title="TTFT 平均延迟 (Experiment)"
                            value={report?.['TTFT (Baseline)']?.experiment?.mean || 0}
                            precision={1}
                            suffix="ms"
                            prefix={<Zap size={18} color="var(--ant-color-success)" />}
                        />
                        <div style={{ marginTop: 8 }}>
                            {report?.['TTFT (Baseline)']?.experiment && report?.['TTFT (Baseline)']?.control && (
                                <Badge 
                                    status={report['TTFT (Baseline)'].experiment.mean < report['TTFT (Baseline)'].control.mean ? 'success' : 'error'}
                                    text={`性能变化: ${((report['TTFT (Baseline)'].experiment.mean - report['TTFT (Baseline)'].control.mean) / report['TTFT (Baseline)'].control.mean * 100).toFixed(1)}%`}
                                />
                            )}
                        </div>
                    </Card>
                </Col>
                <Col span={8}>
                    <Card bordered={false}>
                        <Statistic
                            title="诊断置信度"
                            value={diagnosis?.status === 'HEALTHY' ? 'HIGH' : 'MEDIUM'}
                            prefix={<ShieldAlert size={18} color={diagnosis?.status === 'HEALTHY' ? 'var(--ant-color-success)' : 'var(--ant-color-warning)'} />}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 第二排：A/B 对视图与 HMER 审计 */}
            <Row gutter={24} style={{ marginTop: '24px' }}>
                <Col span={10}>
                    <Card title="A/B 性能对比可视化 (Mean Latency)" bordered={false} style={{ height: '550px' }}>
                        {loadingReport ? (
                            <div style={{ textAlign: 'center', paddingTop: '100px' }}><Spin size="large" /></div>
                        ) : chartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={450}>
                                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="name" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Bar dataKey="control" name="对照组 (Control)" fill="var(--ant-color-text-quaternary)" radius={[4, 4, 0, 0]} />
                                    <Bar dataKey="experiment" name="实验组 (Experiment)" fill="var(--ant-color-success)" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <Empty description="暂无 A/B 对比数据" />
                        )}
                    </Card>
                </Col>

                <Col span={14}>
                    <Card 
                        title={
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Cpu size={18} />
                                HMER 阶段准出审计报告 (Phase 0 {"->"} 1)
                            </div>
                        }
                        bordered={false} 
                        style={{ height: '550px', overflowY: 'auto', borderLeft: '4px solid var(--ant-color-primary)' }}
                        extra={
                            phaseAudit?.ready_to_proceed ? 
                            <Badge status="success" text="可以进入 Phase 1" /> : 
                            <Badge status="default" text="等待样本充足" />
                        }
                    >
                        {loadingAudit ? (
                            <div style={{ textAlign: 'center', paddingTop: '100px' }}>
                                <Spin tip="AI 审计员正在整理反思报告..." size="large" />
                            </div>
                        ) : phaseAudit?.audit_report ? (
                            <div className="hmer-audit-content">
                                <ReactMarkdown>{phaseAudit.audit_report}</ReactMarkdown>
                                
                                <Divider />
                                <div style={{ textAlign: 'right' }}>
                                    <Button type="primary" size="large" disabled={!phaseAudit.ready_to_proceed}>
                                        确认收妥反思，开启 Phase 1 架构重构
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <Empty description="等待采集足够数据后开启阶段审计" />
                        )}
                    </Card>
                </Col>
            </Row>

            {/* 第三排：Phase 4 预测性分析 */}
            <Row gutter={16} style={{ marginTop: '24px' }}>
                <Col span={24}>
                    <Card title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <RefreshCw size={18} />
                            Phase 4: 预测性加载效能分析 (Predictive Prefetching)
                        </div>
                    } bordered={false}>
                        <Row gutter={24}>
                            <Col span={6}>
                                <Statistic 
                                    title="意图触发总数" 
                                    value={128} 
                                    prefix={<Cpu size={14} />} 
                                    suffix="Counts"
                                />
                                <div style={{ marginTop: 4 }}>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>过去 1 小时内全站触发的 Hover/Focus 预测</Text>
                                </div>
                            </Col>
                            <Col span={6}>
                                <Statistic 
                                    title="预测命中率 (Hits)" 
                                    value={84.5} 
                                    precision={1}
                                    suffix="%"
                                    valueStyle={{ color: 'var(--ant-color-success)' }}
                                />
                                <div style={{ marginTop: 4 }}>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>预测加载后 2 秒内产生真实点击的比例</Text>
                                </div>
                            </Col>
                            <Col span={6}>
                                <Statistic 
                                    title="平均节省首字节时间 (Saved)" 
                                    value={320} 
                                    suffix="ms"
                                />
                                <div style={{ marginTop: 4 }}>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>通过提前预热 React Query 节省的感知延迟</Text>
                                </div>
                            </Col>
                            <Col span={6}>
                                <Statistic 
                                    title="异常浪费率" 
                                    value={5.2} 
                                    precision={1}
                                    suffix="%"
                                    valueStyle={{ color: 'var(--ant-color-warning)' }}
                                />
                                <div style={{ marginTop: 4 }}>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>已预测加载但最终未点击导致的网络冗余</Text>
                                </div>
                            </Col>
                        </Row>
                    </Card>
                </Col>
            </Row>

            <Divider>HMER Reconstruction Roadmap (Phase 1-3)</Divider>
            <Paragraph type="secondary" style={{ textAlign: 'center' }}>
                A/B 对比能力允许架构师在合并代码前，在局部沙盒环境中验证改造收益。
            </Paragraph>
        </div>
    );
};

export default ArchitectureLabPage;
