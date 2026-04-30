/**
 * UsagePage — per-tenant token / cost dashboard.
 *
 * Shows:
 *   - Today's progress bars (tokens + $-spend) with warn-threshold marker
 *   - Quota / rate-limit summary
 *   - 30-day sparklines (tokens, requests, cost) — raw SVG, no chart lib
 *
 * @see backend/app/api/routes/tenants.py
 * @see TODO.md > 2.0c (frontend dashboard)
 */

import { useEffect, useState, useMemo } from 'react';
import {
    Card, Row, Col, Progress, Statistic, Tag, Space, Typography, Button, Alert, Spin, Tooltip,
} from 'antd';
import { ReloadOutlined, ThunderboltOutlined, DollarOutlined } from '@ant-design/icons';

import {
    getMyUsage, getMyUsageHistory, formatCostMicro,
    type UsageSnapshot, type UsageHistory, type UsageHistoryPoint,
} from '../services/tenantsApi';

const { Title, Text } = Typography;

// ----- Sparkline (no chart lib) -----
function Sparkline({
    points, accessor, color, height = 48, label,
}: {
    points: UsageHistoryPoint[];
    accessor: (p: UsageHistoryPoint) => number;
    color: string;
    height?: number;
    label: string;
}) {
    const width = 320;
    const padding = 4;
    const values = points.map(accessor);
    const max = Math.max(1, ...values);

    const stepX = points.length > 1 ? (width - padding * 2) / (points.length - 1) : 0;
    const toY = (v: number) =>
        height - padding - ((v / max) * (height - padding * 2));

    const path = points
        .map((p, i) => `${i === 0 ? 'M' : 'L'}${padding + i * stepX},${toY(accessor(p))}`)
        .join(' ');
    const fillPath = `${path} L${padding + (points.length - 1) * stepX},${height - padding} L${padding},${height - padding} Z`;

    return (
        <div>
            <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
            <svg width={width} height={height} style={{ display: 'block', marginTop: 4 }}>
                <path d={fillPath} fill={color} fillOpacity={0.15} />
                <path d={path} stroke={color} strokeWidth={1.5} fill="none" />
            </svg>
        </div>
    );
}

export function UsagePage() {
    const [snap, setSnap] = useState<UsageSnapshot | null>(null);
    const [history, setHistory] = useState<UsageHistory | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = async () => {
        try {
            setLoading(true);
            setError(null);
            const [s, h] = await Promise.all([
                getMyUsage(),
                getMyUsageHistory(30),
            ]);
            setSnap(s);
            setHistory(h);
        } catch (e: unknown) {
            const msg =
                (e as { response?: { data?: { message?: string } }; message?: string })
                    ?.response?.data?.message
                ?? (e as { message?: string })?.message
                ?? '加载失败';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void load();
        // Auto-refresh every 30s so the live counter stays fresh
        const id = setInterval(() => void load(), 30_000);
        return () => clearInterval(id);
    }, []);

    const tokenStatus = useMemo<'normal' | 'warning' | 'danger'>(() => {
        if (!snap?.quota_used_pct) return 'normal';
        if (snap.quota_used_pct >= 100) return 'danger';
        if (snap.quota_used_pct >= (snap.warn_threshold_pct ?? 80)) return 'warning';
        return 'normal';
    }, [snap]);

    const costStatus = useMemo<'normal' | 'warning' | 'danger'>(() => {
        if (!snap?.quota_cost_used_pct) return 'normal';
        if (snap.quota_cost_used_pct >= 100) return 'danger';
        if (snap.quota_cost_used_pct >= (snap.warn_threshold_pct ?? 80)) return 'warning';
        return 'normal';
    }, [snap]);

    if (loading && !snap) return <Spin tip="加载用量..." style={{ display: 'block', margin: 64 }} />;
    if (error) return <Alert type="error" message={error} showIcon />;
    if (!snap) return null;

    const isUnlimited = !snap.quota_tokens_per_day;
    const isCostUnlimited = !snap.quota_cost_usd_micro_per_day;

    return (
        <div style={{ padding: 16 }}>
            <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
                <Title level={3} style={{ margin: 0 }}>用量与配额 · {snap.tenant_id}</Title>
                <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
            </Space>

            {/* Today's snapshot */}
            <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                    <Card>
                        <Statistic
                            title="今日 Token 用量"
                            value={snap.total_tokens}
                            prefix={<ThunderboltOutlined />}
                            suffix={isUnlimited ? '/ ∞' : `/ ${snap.quota_tokens_per_day?.toLocaleString()}`}
                        />
                        {!isUnlimited && (
                            <Progress
                                percent={Math.min(100, snap.quota_used_pct ?? 0)}
                                status={
                                    tokenStatus === 'danger' ? 'exception' :
                                    tokenStatus === 'warning' ? 'active' : 'normal'
                                }
                                strokeColor={
                                    tokenStatus === 'danger' ? '#EF476F' :
                                    tokenStatus === 'warning' ? '#FFD166' : '#06D6A0'
                                }
                                style={{ marginTop: 12 }}
                            />
                        )}
                        <Space size="small" style={{ marginTop: 8 }}>
                            <Tag color="blue">prompt: {snap.prompt_tokens.toLocaleString()}</Tag>
                            <Tag color="purple">completion: {snap.completion_tokens.toLocaleString()}</Tag>
                            <Tag>requests: {snap.request_count}</Tag>
                        </Space>
                    </Card>
                </Col>

                <Col xs={24} md={12}>
                    <Card>
                        <Statistic
                            title="今日 $-花费"
                            value={formatCostMicro(snap.cost_usd_micro)}
                            prefix={<DollarOutlined />}
                            suffix={
                                isCostUnlimited
                                    ? '/ ∞'
                                    : `/ ${formatCostMicro(snap.quota_cost_usd_micro_per_day ?? 0)}`
                            }
                        />
                        {!isCostUnlimited && (
                            <Progress
                                percent={Math.min(100, snap.quota_cost_used_pct ?? 0)}
                                status={
                                    costStatus === 'danger' ? 'exception' :
                                    costStatus === 'warning' ? 'active' : 'normal'
                                }
                                strokeColor={
                                    costStatus === 'danger' ? '#EF476F' :
                                    costStatus === 'warning' ? '#FFD166' : '#06D6A0'
                                }
                                style={{ marginTop: 12 }}
                            />
                        )}
                        {snap.warn_threshold_pct ? (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                ⚠️ 预警阈值: {snap.warn_threshold_pct}%
                            </Text>
                        ) : null}
                    </Card>
                </Col>
            </Row>

            {/* Quota & rate limit summary */}
            <Card title="配额与限流" style={{ marginTop: 16 }}>
                <Row gutter={[16, 16]}>
                    <Col xs={12} md={6}>
                        <Tooltip title="每秒最大请求数 (sliding window)">
                            <Statistic
                                title="RPS 上限"
                                value={snap.quota_max_rps ?? '—'}
                                valueStyle={{ fontSize: 18 }}
                            />
                        </Tooltip>
                    </Col>
                    <Col xs={12} md={6}>
                        <Tooltip title="每分钟最大请求数 (sliding window)">
                            <Statistic
                                title="RPM 上限"
                                value={snap.quota_max_rpm ?? '—'}
                                valueStyle={{ fontSize: 18 }}
                            />
                        </Tooltip>
                    </Col>
                    <Col xs={12} md={6}>
                        <Tooltip title="单用户当日 token 上限 (防单一账号耗尽租户配额)">
                            <Statistic
                                title="单用户/日 token"
                                value={snap.quota_max_tokens_per_user_per_day?.toLocaleString() ?? '—'}
                                valueStyle={{ fontSize: 18 }}
                            />
                        </Tooltip>
                    </Col>
                    <Col xs={12} md={6}>
                        <Tooltip title="单会话 token 上限 (lifetime, 非按日)">
                            <Statistic
                                title="单会话 token"
                                value={snap.quota_max_tokens_per_conversation?.toLocaleString() ?? '—'}
                                valueStyle={{ fontSize: 18 }}
                            />
                        </Tooltip>
                    </Col>
                </Row>
            </Card>

            {/* 30-day sparklines */}
            {history && history.points.length > 0 && (
                <Card title="近 30 天趋势" style={{ marginTop: 16 }}>
                    <Row gutter={[16, 16]}>
                        <Col xs={24} md={8}>
                            <Sparkline
                                points={history.points}
                                accessor={(p) => p.total_tokens}
                                color="#06D6A0"
                                label="Total tokens / day"
                            />
                        </Col>
                        <Col xs={24} md={8}>
                            <Sparkline
                                points={history.points}
                                accessor={(p) => p.request_count}
                                color="#118AB2"
                                label="Requests / day"
                            />
                        </Col>
                        <Col xs={24} md={8}>
                            <Sparkline
                                points={history.points}
                                accessor={(p) => p.cost_usd_micro}
                                color="#FFD166"
                                label="Cost (μUSD) / day"
                            />
                        </Col>
                    </Row>
                </Card>
            )}
        </div>
    );
}

export default UsagePage;
