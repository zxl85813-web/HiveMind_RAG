import React, { useState } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, List, Typography, Space, Select, Empty, theme, Progress, Flex } from 'antd';
import { 
    DashboardOutlined, 
    FireOutlined, 
    DisconnectOutlined, 
    AreaChartOutlined, 
    SearchOutlined,
    ClockCircleOutlined,
    ExclamationCircleOutlined,
    AimOutlined,
    DatabaseOutlined
} from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { useKBAnalytics } from '../hooks/queries/useDashboardQuery';
import { knowledgeApi } from '../services/knowledgeApi';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

import { useMonitor } from '../hooks/useMonitor';

const { Title, Text } = Typography;

export const KBAnalyticsPage: React.FC = () => {
    const { track } = useMonitor();

    React.useEffect(() => {
        track('system', 'page_load', { page: 'KBAnalytics' });
    }, [track]);

    const { token } = theme.useToken();
    const [selectedKbId, setSelectedKbId] = useState<string | undefined>(undefined);
    const [days, setDays] = useState(7);

    // Fetch KB list for selector
    const { data: kbsRes } = useQuery({
        queryKey: ['kbs'],
        queryFn: () => knowledgeApi.listKBs(),
    });
    const kbs = kbsRes?.data?.data || [];

    const { data: analytics, isLoading } = useKBAnalytics(selectedKbId, days);

    const quality = analytics?.quality || {};
    const hotQueries = analytics?.hotQueries || [];
    const coldDocuments = analytics?.coldDocuments || [];

    const hotQueryColumns = [
        { title: '查询语句 (Query)', dataIndex: 'query', key: 'query', ellipsis: true },
        { title: '查询次数', dataIndex: 'count', key: 'count', sorter: (a: any, b: any) => a.count - b.count, width: 120 },
        { 
            title: '排名', 
            dataIndex: 'rank', 
            key: 'rank', 
            width: 80, 
            render: (r: number) => <Tag color={r <= 3 ? 'volcano' : 'default'}>{r}</Tag> 
        }
    ];

    const coldDocColumns = [
        { title: '文件 ID', dataIndex: 'doc_id', key: 'id', ellipsis: true },
        { title: '检索次数', dataIndex: 'retrieval_count', key: 'count', sorter: (a: any, b: any) => a.retrieval_count - b.retrieval_count, width: 120 },
        { 
            title: '状态', 
            key: 'status', 
            render: (record: any) => record.retrieval_count === 0 ? <Tag color="error">从未被调用</Tag> : <Tag color="warning">低频</Tag> 
        }
    ];

    return (
        <PageContainer
            title="知识库质量分析看板 (M5.2.4)"
            description="全方位透视知识库检索效率、热门趋势与冗余资产，辅助提升 RAG 系统的信噪比。"
            actions={
                <Space>
                    <Select
                        placeholder="选择知识库 (全局)"
                        allowClear
                        style={{ width: 220 }}
                        onChange={setSelectedKbId}
                        options={kbs.map(kb => ({ label: kb.name, value: kb.id }))}
                    />
                    <Select
                        defaultValue={7}
                        style={{ width: 120 }}
                        onChange={setDays}
                        options={[
                            { label: '最近 1 天', value: 1 },
                            { label: '最近 7 天', value: 7 },
                            { label: '最近 30 天', value: 30 },
                            { label: '最近 90 天', value: 90 },
                        ]}
                    />
                </Space>
            }
        >
            <Row gutter={[16, 16]}>
                {/* 1. Core Metrics */}
                <Col span={6}>
                    <Card bordered={false} hoverable>
                        <Statistic
                            title="检索命中率 (Hit Rate)"
                            value={(quality.hit_rate || 0) * 100}
                            precision={1}
                            suffix="%"
                            prefix={<AimOutlined style={{ color: token.colorSuccess }} />}
                            valueStyle={{ color: token.colorSuccess }}
                        />
                        <Progress percent={Math.round((quality.hit_rate || 0) * 100)} size="small" strokeColor={token.colorSuccess} showInfo={false} />
                        <Text type="secondary" style={{ fontSize: 12 }}>{quality.total_queries || 0} 次总查询中命中 {Math.round((quality.hit_rate || 0) * (quality.total_queries || 0))} 次</Text>
                    </Card>
                </Col>
                <Col span={6}>
                    <Card bordered={false} hoverable>
                        <Statistic
                            title="平均检索延迟"
                            value={quality.avg_latency_ms || 0}
                            precision={0}
                            suffix="ms"
                            prefix={<ClockCircleOutlined style={{ color: token.colorInfo }} />}
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>包含向量检索 + 重排的全链路耗时</Text>
                    </Card>
                </Col>
                <Col span={6}>
                    <Card bordered={false} hoverable>
                        <Statistic
                            title="无结果率 (Empty)"
                            value={(quality.empty_result_rate || 0) * 100}
                            precision={1}
                            suffix="%"
                            prefix={<ExclamationCircleOutlined style={{ color: token.colorWarning }} />}
                            valueStyle={{ color: quality.empty_result_rate > 0.3 ? token.colorError : token.colorWarning }}
                        />
                        <Progress percent={Math.round((quality.empty_result_rate || 0) * 100)} size="small" strokeColor={token.colorWarning} showInfo={false} />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card bordered={false} hoverable>
                        <Statistic
                            title="查询报错率"
                            value={(quality.error_rate || 0) * 100}
                            precision={2}
                            suffix="%"
                            prefix={<ExclamationCircleOutlined style={{ color: token.colorError }} />}
                            valueStyle={{ color: token.colorError }}
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>通常由模型熔断或数据库超时引起</Text>
                    </Card>
                </Col>

                {/* 2. Hot Queries & Cold Docs */}
                <Col span={14}>
                    <Card 
                        title={<Flex align="center" gap={8}><FireOutlined style={{ color: token.colorWarning }} /> 热门查询趋势 (Understanding User Intent)</Flex>}
                        bordered={false}
                        styles={{ body: { padding: 0 } }}
                    >
                        <div style={{ padding: '24px', height: 320 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={hotQueries.slice(0, 10)}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                                    <XAxis 
                                        dataKey="query" 
                                        tick={{ fill: 'rgba(255,255,255,0.45)', fontSize: 11 }} 
                                        axisLine={false}
                                        tickLine={false}
                                        interval={0}
                                        angle={-15}
                                        textAnchor="end"
                                    />
                                    <YAxis tick={{ fill: 'rgba(255,255,255,0.45)', fontSize: 11 }} axisLine={false} tickLine={false} />
                                    <Tooltip 
                                        contentStyle={{ backgroundColor: 'var(--hm-color-bg-elevated)', border: 'none', borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}
                                        itemStyle={{ color: 'var(--hm-color-text)' }}
                                    />
                                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                        {hotQueries.map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={index < 3 ? token.colorWarning : token.colorInfo} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                        <Table 
                            dataSource={hotQueries} 
                            columns={hotQueryColumns} 
                            rowKey="query" 
                            size="small" 
                            pagination={{ pageSize: 5 }} 
                            style={{ margin: '0 12px 12px' }}
                        />
                    </Card>
                </Col>

                <Col span={10}>
                    <Card 
                        title={<Flex align="center" gap={8}><DisconnectOutlined style={{ color: token.colorWarning }} /> 冷门资产分析 (Knowledge Cleanup)</Flex>}
                        bordered={false}
                        extra={<Text type="secondary" style={{ fontSize: 11 }}>最少被检索的 Top 20 文档</Text>}
                    >
                        {!selectedKbId ? (
                            <Empty description="请先选择具体的知识库以分析文档冷度" style={{ padding: '40px 0' }} />
                        ) : (
                            <Table 
                                dataSource={coldDocuments} 
                                columns={coldDocColumns} 
                                rowKey="doc_id" 
                                size="small" 
                                pagination={{ pageSize: 8 }} 
                                loading={isLoading}
                            />
                        )}
                        <Card 
                            size="small" 
                            style={{ marginTop: 16, background: 'rgba(250, 173, 20, 0.05)', border: '1px dashed rgba(250, 173, 20, 0.2)' }}
                        >
                            <Space align="start">
                                <ExclamationCircleOutlined style={{ color: token.colorWarning, marginTop: 4 }} />
                                <div>
                                    <Text strong style={{ display: 'block' }}>治理建议</Text>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        上述冷门文档可能已过期或分块逻辑存在缺陷。建议进行 `TruthAlignment` 验证或删除冗余资产以提升检索精度。
                                    </Text>
                                </div>
                            </Space>
                        </Card>
                    </Card>
                </Col>

                {/* 3. Global Perspective */}
                <Col span={24}>
                    <Card title={<Flex align="center" gap={8}><AreaChartOutlined /> 检索系统健康度评估报告</Flex>} bordered={false}>
                        <Row gutter={48}>
                            <Col span={12}>
                                <Title level={5}>现状诊断</Title>
                                <List size="small">
                                    <List.Item>
                                        <Text>系统当前命中率为 <Text strong color={token.colorSuccess}>{Math.round((quality.hit_rate || 0) * 100)}%</Text>，处于 {quality.hit_rate > 0.8 ? '优秀' : quality.hit_rate > 0.6 ? '良好' : '亚健康'} 水平。</Text>
                                    </List.Item>
                                    <List.Item>
                                        <Text>空结果率为 <Text strong>{Math.round((quality.empty_result_rate || 0) * 100)}%</Text>，{quality.empty_result_rate > 0.2 ? '反映出部分用户需求超出了现有知识库覆盖范围。' : '表现稳健。'}</Text>
                                    </List.Item>
                                    <List.Item>
                                        <Text>冷门文档占比显著，建议对无检索记录的文档执行一次人工采样抽查。</Text>
                                    </List.Item>
                                </List>
                            </Col>
                            <Col span={12}>
                                <Title level={5}>治理工具引导 (Next Action)</Title>
                                <Space wrap>
                                    <Tag icon={<SearchOutlined />} color="processing" style={{ padding: '8px 16px', borderRadius: 8, cursor: 'pointer' }}>启动全链路 Trace 分析</Tag>
                                    <Tag icon={<DatabaseOutlined />} color="success" style={{ padding: '8px 16px', borderRadius: 8, cursor: 'pointer' }}>进入 Code Vault 检查关联</Tag>
                                    <Tag icon={<DashboardOutlined />} color="warning" style={{ padding: '8px 16px', borderRadius: 8, cursor: 'pointer' }}>更新限流与路由策略</Tag>
                                </Space>
                            </Col>
                        </Row>
                    </Card>
                </Col>
            </Row>
        </PageContainer>
    );
};
