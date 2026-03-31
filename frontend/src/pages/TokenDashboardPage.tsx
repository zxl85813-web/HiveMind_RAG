import React, { useState } from 'react';
import { Row, Col, Card, Typography, Table, Tag, Segmented, Space, Empty } from 'antd';
import { 
    ThunderboltOutlined, 
    DollarOutlined, 
    HistoryOutlined, 
    BarChartOutlined,
    GlobalOutlined 
} from '@ant-design/icons';
import { 
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
    PieChart, Pie, Cell, Legend 
} from 'recharts';
import { PageContainer, StatCard } from '../components/common';
import { useLLMMetrics } from '../hooks/queries/useDashboardQuery';

const { Text } = Typography;

const COLORS = [
    'var(--hm-color-success)', 
    'var(--hm-color-brand)', 
    'var(--hm-color-warning)', 
    'var(--hm-color-error)', 
    'var(--hm-color-purple)'
];

/**
 * 🛰️ [M5.2.1]: Token 实时大屏 — 基于 TokenUsage 独立表的实时成本监控。
 */
export const TokenDashboardPage: React.FC = () => {
    const [days, setDays] = useState<number>(1);
    const { data: metrics = [], isLoading } = useLLMMetrics(days);

    // 计算全局指标
    const totalTokens = metrics.reduce((acc, m) => acc + m.total_tokens, 0);
    const totalCost = metrics.reduce((acc, m) => acc + (m.cost || 0), 0);
    const avgLatency = metrics.length > 0 
        ? metrics.reduce((acc, m) => acc + m.avg_latency, 0) / metrics.length 
        : 0;
    const globalSuccessRate = metrics.length > 0
        ? metrics.reduce((acc, m) => acc + m.success_rate, 0) / metrics.length
        : 1;

    // 格式化图表数据
    const barData = metrics.map(m => ({
        name: m.model_name,
        tokens: m.total_tokens,
        latency: m.avg_latency,
    }));

    const pieData = metrics.map(m => ({
        name: m.model_name,
        value: m.total_tokens,
    }));

    const columns = [
        {
            title: '模型名称',
            dataIndex: 'model_name',
            key: 'model_name',
            render: (text: string) => <Text strong>{text}</Text>,
        },
        {
            title: '供应商',
            dataIndex: 'provider',
            key: 'provider',
            render: (text: string) => <Tag color="blue">{text.toUpperCase()}</Tag>,
        },
        {
            title: '总调用量',
            dataIndex: 'total_calls',
            key: 'total_calls',
            sorter: (a: any, b: any) => a.total_calls - b.total_calls,
        },
        {
            title: '消耗 Token',
            dataIndex: 'total_tokens',
            key: 'total_tokens',
            render: (val: number) => val.toLocaleString(),
            sorter: (a: any, b: any) => a.total_tokens - b.total_tokens,
        },
        {
            title: '平均延迟',
            dataIndex: 'avg_latency',
            key: 'avg_latency',
            render: (val: number) => `${val.toFixed(0)} ms`,
            sorter: (a: any, b: any) => a.avg_latency - b.avg_latency,
        },
        {
            title: '成功率',
            dataIndex: 'success_rate',
            key: 'success_rate',
            render: (val: number) => (
                <Tag color={val > 0.98 ? 'success' : val > 0.9 ? 'warning' : 'error'}>
                    {(val * 100).toFixed(1)}%
                </Tag>
            ),
        }
    ];

    return (
        <PageContainer 
            title="Token 实时大屏" 
            actions={
                <Space>
                    <Text type="secondary"><HistoryOutlined /> 统计窗口:</Text>
                    <Segmented 
                        options={[
                            { label: '24小时', value: 1 },
                            { label: '7天', value: 7 },
                            { label: '30天', value: 30 }
                        ]} 
                        value={days}
                        onChange={(val) => setDays(val as number)}
                    />
                </Space>
            }
        >
            {/* === 核心指标 === */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} md={6}>
                    <StatCard 
                        title="累计消耗 Token" 
                        value={totalTokens.toLocaleString()} 
                        icon={<ThunderboltOutlined />} 
                        color="primary"
                        loading={isLoading}
                    />
                </Col>
                <Col xs={24} md={6}>
                    <StatCard 
                        title="预估总支出" 
                        value={`$${totalCost.toFixed(4)}`} 
                        icon={<DollarOutlined />} 
                        color="warning"
                        loading={isLoading}
                    />
                </Col>
                <Col xs={24} md={6}>
                    <StatCard 
                        title="平均响应延迟" 
                        value={`${avgLatency.toFixed(0)} ms`} 
                        icon={<BarChartOutlined />} 
                        color="info"
                        loading={isLoading}
                    />
                </Col>
                <Col xs={24} md={6}>
                    <StatCard 
                        title="智体运行健康度" 
                        value={`${(globalSuccessRate * 100).toFixed(1)}%`} 
                        icon={<GlobalOutlined />} 
                        color="success"
                        loading={isLoading}
                    />
                </Col>
            </Row>

            {/* === 图表分析 === */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={16}>
                    <Card title="模型 Token 消耗分布" style={{ height: 400 }}>
                        {metrics.length > 0 ? (
                            <ResponsiveContainer width="100%" height={320}>
                                <BarChart data={barData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--hm-color-text-secondary)', fontSize: 12 }} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--hm-color-text-secondary)', fontSize: 12 }} />
                                    <Tooltip 
                                        contentStyle={{ backgroundColor: 'var(--hm-color-bg-elevated)', border: 'none', borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}
                                        itemStyle={{ color: 'var(--hm-color-text)' }}
                                    />
                                    <Bar dataKey="tokens" fill="var(--hm-color-brand)" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
                    </Card>
                </Col>
                <Col xs={24} lg={8}>
                    <Card title="模型占比 (Tokens)" style={{ height: 400 }}>
                        {metrics.length > 0 ? (
                            <ResponsiveContainer width="100%" height={320}>
                                <PieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={80}
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {pieData.map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                    <Legend />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
                    </Card>
                </Col>
            </Row>

            {/* === 详细明细 === */}
            <Card title="模型看板明细">
                <Table 
                    columns={columns} 
                    dataSource={metrics} 
                    rowKey="model_name" 
                    loading={isLoading}
                    pagination={false}
                    size="middle"
                />
            </Card>
        </PageContainer>
    );
};
