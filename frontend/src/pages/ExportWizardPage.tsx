/**
 * ExportWizardPage — visual blueprint authoring + one-click export.
 *
 * Three-step wizard (intentionally compact for MVP):
 *   1. Basics & LLM      — name, customer, platform/UI mode, LLM provider+model
 *   2. Assets            — pick agent skills + MCP servers from the catalog
 *   3. Review & Export   — show generated YAML, submit job, stream progress
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
    App,
    Button,
    Card,
    Col,
    Empty,
    Form,
    Input,
    Progress,
    Radio,
    Row,
    Select,
    Space,
    Steps,
    Tag,
    Typography,
    Alert,
    Divider,
    Tooltip,
    Flex,
} from 'antd';
import {
    DownloadOutlined,
    PlayCircleOutlined,
    ReloadOutlined,
    RocketOutlined,
} from '@ant-design/icons';
import {
    exportApi,
    type AssetCatalog,
    type BlueprintDraft,
    type ExportJob,
    type LLMProvider,
    type PlatformMode,
    type UIMode,
} from '../services/exportApi';
import { useBlueprintStore } from '../stores/blueprintStore';

const { Title, Text, Paragraph } = Typography;

const PLATFORM_OPTIONS: { value: PlatformMode; label: string; hint: string }[] = [
    { value: 'agent', label: 'Agent', hint: '单 Agent / 多 Agent 编排，最常见' },
    { value: 'rag', label: 'RAG', hint: '纯知识库检索' },
    { value: 'full', label: 'Full', hint: 'RAG + Agent 全功能' },
];

const UI_MODE_OPTIONS: { value: UIMode; label: string; hint: string }[] = [
    { value: 'single_agent', label: 'Single Agent', hint: '只渲染一个对话窗口' },
    { value: 'full', label: 'Full', hint: '完整侧边栏布局' },
    { value: 'widget', label: 'Widget', hint: '可嵌入式 widget（外部 build）' },
];

const LLM_PROVIDERS: { value: LLMProvider; label: string }[] = [
    { value: 'openai', label: 'OpenAI 兼容' },
    { value: 'ark', label: '火山方舟 (Ark)' },
    { value: 'local_vllm', label: '本地 vLLM' },
    { value: 'ollama', label: 'Ollama' },
    { value: 'other', label: '其它' },
];

/** Render a draft as YAML-ish text for preview (no extra dep). */
function blueprintToYaml(draft: BlueprintDraft): string {
    const lines: string[] = [];
    lines.push(`name: ${draft.name}`);
    lines.push(`version: ${draft.version}`);
    lines.push(`customer: ${draft.customer || '(unset)'}`);
    if (draft.description) {
        lines.push('description: |');
        for (const ln of draft.description.split('\n')) lines.push(`  ${ln}`);
    }
    lines.push(`platform_mode: ${draft.platform_mode}`);
    lines.push(`ui_mode: ${draft.ui_mode}`);
    lines.push('llm:');
    lines.push(`  provider: ${draft.llm.provider}`);
    lines.push(`  model: ${draft.llm.model}`);
    if (draft.llm.base_url) lines.push(`  base_url: ${draft.llm.base_url}`);
    lines.push('agents:');
    for (const a of draft.agents) {
        lines.push(`  - id: ${a.id}`);
        lines.push(`    name: ${a.name}`);
        if (a.system_prompt) {
            lines.push('    system_prompt: |');
            for (const ln of a.system_prompt.split('\n')) lines.push(`      ${ln}`);
        }
        lines.push(`    skills: [${a.skills.join(', ')}]`);
        lines.push(`    mcp_servers: [${a.mcp_servers.join(', ')}]`);
    }
    if (draft.default_agent_id) lines.push(`default_agent_id: ${draft.default_agent_id}`);
    const envKeys = Object.entries(draft.env_overrides).filter(([, v]) => v !== null && v !== '');
    if (envKeys.length) {
        lines.push('env_overrides:');
        for (const [k, v] of envKeys) lines.push(`  ${k}: ${v}`);
    }
    return lines.join('\n');
}

/** Step 1 — Basics + LLM */
const StepBasics: React.FC = () => {
    const { draft, setDraft, upsertAgent } = useBlueprintStore();
    return (
        <Form layout="vertical">
            <Row gutter={16}>
                <Col span={12}>
                    <Form.Item label="交付物名称 (slug)" required>
                        <Input
                            value={draft.name}
                            onChange={(e) => setDraft({ name: e.target.value })}
                            placeholder="quote-bot"
                        />
                    </Form.Item>
                </Col>
                <Col span={6}>
                    <Form.Item label="版本">
                        <Input
                            value={draft.version}
                            onChange={(e) => setDraft({ version: e.target.value })}
                        />
                    </Form.Item>
                </Col>
                <Col span={6}>
                    <Form.Item label="客户" required>
                        <Input
                            value={draft.customer}
                            onChange={(e) => setDraft({ customer: e.target.value })}
                            placeholder="ACME"
                        />
                    </Form.Item>
                </Col>
            </Row>
            <Form.Item label="描述">
                <Input.TextArea
                    rows={2}
                    value={draft.description}
                    onChange={(e) => setDraft({ description: e.target.value })}
                />
            </Form.Item>

            <Divider orientation="left" plain>
                平台模式 / UI 模式
            </Divider>
            <Row gutter={16}>
                <Col span={12}>
                    <Form.Item label="后端 platform_mode">
                        <Radio.Group
                            value={draft.platform_mode}
                            onChange={(e) => setDraft({ platform_mode: e.target.value })}
                        >
                            {PLATFORM_OPTIONS.map((o) => (
                                <Tooltip key={o.value} title={o.hint}>
                                    <Radio.Button value={o.value}>{o.label}</Radio.Button>
                                </Tooltip>
                            ))}
                        </Radio.Group>
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item label="前端 ui_mode">
                        <Radio.Group
                            value={draft.ui_mode}
                            onChange={(e) => setDraft({ ui_mode: e.target.value })}
                        >
                            {UI_MODE_OPTIONS.map((o) => (
                                <Tooltip key={o.value} title={o.hint}>
                                    <Radio.Button value={o.value}>{o.label}</Radio.Button>
                                </Tooltip>
                            ))}
                        </Radio.Group>
                    </Form.Item>
                </Col>
            </Row>

            <Divider orientation="left" plain>
                LLM
            </Divider>
            <Row gutter={16}>
                <Col span={8}>
                    <Form.Item label="Provider">
                        <Select
                            value={draft.llm.provider}
                            options={LLM_PROVIDERS}
                            onChange={(v) =>
                                setDraft({ llm: { ...draft.llm, provider: v as LLMProvider } })
                            }
                        />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item label="Model">
                        <Input
                            value={draft.llm.model}
                            onChange={(e) =>
                                setDraft({ llm: { ...draft.llm, model: e.target.value } })
                            }
                            placeholder="gpt-4o-mini"
                        />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item
                        label="Base URL"
                        tooltip="内网 vLLM / Ark 代理；留空走默认"
                    >
                        <Input
                            value={draft.llm.base_url || ''}
                            onChange={(e) =>
                                setDraft({
                                    llm: { ...draft.llm, base_url: e.target.value || undefined },
                                })
                            }
                            placeholder="http://intranet-vllm:8000/v1"
                        />
                    </Form.Item>
                </Col>
            </Row>

            <Divider orientation="left" plain>
                默认 Agent
            </Divider>
            <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                message="MVP 仅支持单个默认 Agent；后续会支持多 Agent。"
            />
            <Row gutter={16}>
                <Col span={8}>
                    <Form.Item label="Agent ID">
                        <Input
                            value={draft.agents[0]?.id || ''}
                            onChange={(e) => {
                                upsertAgent(0, { id: e.target.value });
                                setDraft({ default_agent_id: e.target.value });
                            }}
                        />
                    </Form.Item>
                </Col>
                <Col span={16}>
                    <Form.Item label="名称">
                        <Input
                            value={draft.agents[0]?.name || ''}
                            onChange={(e) => upsertAgent(0, { name: e.target.value })}
                        />
                    </Form.Item>
                </Col>
            </Row>
            <Form.Item label="System Prompt">
                <Input.TextArea
                    rows={4}
                    value={draft.agents[0]?.system_prompt || ''}
                    onChange={(e) => upsertAgent(0, { system_prompt: e.target.value })}
                    placeholder="你是 ACME 的销售报价助手……"
                />
            </Form.Item>
        </Form>
    );
};

/** Step 2 — Asset picker (skills + MCP) */
const StepAssets: React.FC<{ catalog: AssetCatalog | null; loading: boolean }> = ({
    catalog,
    loading,
}) => {
    const { draft, upsertAgent } = useBlueprintStore();
    const agent = draft.agents[0];

    if (loading) return <Card loading />;
    if (!catalog) return <Empty description="资产清单加载失败" />;

    return (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Card size="small" title={`Skills（已发现 ${catalog.skills.length} 个）`}>
                <Select
                    mode="multiple"
                    style={{ width: '100%' }}
                    value={agent.skills}
                    onChange={(v) => upsertAgent(0, { skills: v })}
                    placeholder="选择本 Agent 需要的 skill"
                    optionFilterProp="label"
                    options={catalog.skills.map((s) => ({
                        value: s.id,
                        label: s.id,
                        title: s.description,
                    }))}
                />
            </Card>

            <Card size="small" title={`MCP Servers（已发现 ${catalog.mcp_servers.length} 个）`}>
                <Select
                    mode="multiple"
                    style={{ width: '100%' }}
                    value={agent.mcp_servers}
                    onChange={(v) => upsertAgent(0, { mcp_servers: v })}
                    placeholder="选择需要桥接的内部系统（ERP / CRM 等）"
                    optionFilterProp="label"
                    options={catalog.mcp_servers.map((s) => ({
                        value: s.id,
                        label: s.id,
                        title: s.description,
                    }))}
                />
            </Card>

            <Card
                size="small"
                title="额外路径"
                extra={<Text type="secondary">可选</Text>}
            >
                <Select
                    mode="tags"
                    style={{ width: '100%' }}
                    value={draft.extra_paths}
                    onChange={(v) => useBlueprintStore.setState((s) => ({
                        draft: { ...s.draft, extra_paths: v },
                    }))}
                    placeholder="repo-relative 路径，如 prompts/quote_system.md"
                />
            </Card>
        </Space>
    );
};

/** Step 3 — Review + Export */
const StepReview: React.FC<{
    onSubmit: () => Promise<void>;
    submitting: boolean;
    job: ExportJob | null;
}> = ({ onSubmit, submitting, job }) => {
    const { draft } = useBlueprintStore();
    const yaml = useMemo(() => blueprintToYaml(draft), [draft]);

    const progress = useMemo(() => {
        if (!job) return 0;
        if (job.status === 'succeeded') return 100;
        if (job.status === 'failed') return 100;
        // 10 known steps in the packager pipeline.
        const okEvents = job.events.filter((e) => e.status === 'ok').length;
        return Math.min(95, Math.round((okEvents / 10) * 100));
    }, [job]);

    const downloadHref = job?.status === 'succeeded' ? exportApi.downloadUrl(job.id) : null;

    return (
        <Row gutter={16}>
            <Col span={14}>
                <Card
                    size="small"
                    title="blueprint.yaml 预览"
                    extra={<Tag color="cyan">只读</Tag>}
                >
                    <pre
                        style={{
                            background: '#0A0E1A',
                            padding: 12,
                            borderRadius: 8,
                            maxHeight: 480,
                            overflow: 'auto',
                            margin: 0,
                            fontFamily: 'JetBrains Mono, Menlo, monospace',
                            fontSize: 12,
                            color: '#94A3B8',
                            whiteSpace: 'pre',
                        }}
                    >
                        {yaml}
                    </pre>
                </Card>
            </Col>
            <Col span={10}>
                <Card size="small" title="导出">
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        <Button
                            type="primary"
                            icon={<RocketOutlined />}
                            block
                            loading={submitting || job?.status === 'running'}
                            onClick={onSubmit}
                        >
                            {job ? '重新导出' : '开始导出'}
                        </Button>

                        {job && (
                            <>
                                <Progress
                                    percent={progress}
                                    status={
                                        job.status === 'failed'
                                            ? 'exception'
                                            : job.status === 'succeeded'
                                              ? 'success'
                                              : 'active'
                                    }
                                />
                                <div
                                    style={{
                                        maxHeight: 220,
                                        overflow: 'auto',
                                        background: '#0A0E1A',
                                        padding: 8,
                                        borderRadius: 6,
                                        fontSize: 12,
                                        fontFamily: 'JetBrains Mono, Menlo, monospace',
                                    }}
                                >
                                    {job.events.length === 0 ? (
                                        <Text type="secondary">等待进度…</Text>
                                    ) : (
                                        job.events.map((e, i) => (
                                            <div key={i}>
                                                <Tag
                                                    color={
                                                        e.status === 'ok'
                                                            ? 'green'
                                                            : e.status === 'warn'
                                                              ? 'gold'
                                                              : e.status === 'error'
                                                                ? 'red'
                                                                : 'blue'
                                                    }
                                                    style={{ marginRight: 4 }}
                                                >
                                                    {e.status}
                                                </Tag>
                                                <Text>{e.step}</Text>
                                                {e.detail && (
                                                    <Text type="secondary"> — {e.detail}</Text>
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>
                                {job.status === 'succeeded' && downloadHref && (
                                    <Button
                                        type="default"
                                        icon={<DownloadOutlined />}
                                        block
                                        href={downloadHref}
                                        target="_blank"
                                        rel="noopener"
                                    >
                                        下载 ZIP（{(job.bytes_written / 1024).toFixed(1)} KB ·{' '}
                                        {job.files_written} 文件）
                                    </Button>
                                )}
                                {job.status === 'failed' && (
                                    <Alert
                                        type="error"
                                        showIcon
                                        message="导出失败"
                                        description={job.error || '未知错误'}
                                    />
                                )}
                                {job.warnings && job.warnings.length > 0 && (
                                    <Alert
                                        type="warning"
                                        showIcon
                                        message={`${job.warnings.length} 条警告`}
                                        description={
                                            <ul style={{ margin: 0, paddingLeft: 16 }}>
                                                {job.warnings.map((w, i) => (
                                                    <li key={i}>{w}</li>
                                                ))}
                                            </ul>
                                        }
                                    />
                                )}
                            </>
                        )}
                    </Space>
                </Card>
            </Col>
        </Row>
    );
};

export const ExportWizardPage: React.FC = () => {
    const { message } = App.useApp();
    const { draft, activeJob, setActiveJob, patchJob, resetDraft } = useBlueprintStore();

    const [step, setStep] = useState(0);
    const [catalog, setCatalog] = useState<AssetCatalog | null>(null);
    const [catalogLoading, setCatalogLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // Load asset catalog once on mount.
    useEffect(() => {
        setCatalogLoading(true);
        exportApi
            .listAssets()
            .then(setCatalog)
            .catch((e) => message.error(`加载资产清单失败: ${e?.message ?? e}`))
            .finally(() => setCatalogLoading(false));
    }, [message]);

    // Stream job progress via SSE; fall back to polling if EventSource fails.
    // NOTE: depend ONLY on job id + initial status so appending events doesn't
    // tear down and recreate the EventSource (which would replay all events).
    const activeJobId = activeJob?.id;
    const activeJobInitialStatus = activeJob?.status;
    useEffect(() => {
        if (!activeJobId) return;
        if (activeJobInitialStatus !== 'pending' && activeJobInitialStatus !== 'running') {
            return;
        }
        const jobId = activeJobId;
        let cancelled = false;
        let es: EventSource | null = null;
        let pollHandle: number | null = null;

        const startPolling = () => {
            if (pollHandle !== null) return;
            const tick = async () => {
                try {
                    const fresh = await exportApi.getJob(jobId);
                    if (cancelled) return;
                    setActiveJob(fresh);
                    if (fresh.status !== 'pending' && fresh.status !== 'running') {
                        if (pollHandle !== null) {
                            clearInterval(pollHandle);
                            pollHandle = null;
                        }
                    }
                } catch (e) {
                    if (cancelled) return;
                    patchJob({ status: 'failed', error: String(e) });
                    if (pollHandle !== null) {
                        clearInterval(pollHandle);
                        pollHandle = null;
                    }
                }
            };
            pollHandle = window.setInterval(tick, 1000);
        };

        try {
            es = new EventSource(exportApi.streamUrl(jobId));

            es.addEventListener('progress', (ev) => {
                if (cancelled) return;
                try {
                    const data = JSON.parse((ev as MessageEvent).data) as {
                        ts: number;
                        step: string;
                        status: 'start' | 'ok' | 'skip' | 'warn' | 'error';
                        detail?: string;
                    };
                    useBlueprintStore.setState((s) => {
                        if (!s.activeJob || s.activeJob.id !== jobId) return s;
                        // Dedupe: SSE may replay events on reconnect (e.g. React
                        // StrictMode double-mount in dev). Skip if we already saw
                        // this exact (ts, step, status) tuple.
                        const key = `${data.ts}|${data.step}|${data.status}`;
                        const dup = s.activeJob.events.some(
                            (e) => `${e.ts}|${e.step}|${e.status}` === key
                        );
                        if (dup) return s;
                        return {
                            activeJob: {
                                ...s.activeJob,
                                status: 'running',
                                events: [
                                    ...s.activeJob.events,
                                    {
                                        ts: data.ts,
                                        step: data.step,
                                        status: data.status,
                                        detail: data.detail,
                                    },
                                ],
                            },
                        };
                    });
                } catch {
                    /* ignore malformed frame */
                }
            });

            es.addEventListener('done', (ev) => {
                if (cancelled) return;
                try {
                    const data = JSON.parse((ev as MessageEvent).data) as {
                        status: 'succeeded' | 'failed';
                        files_written?: number;
                        bytes_written?: number;
                        warnings?: string[];
                        error?: string | null;
                        zip_path?: string | null;
                    };
                    patchJob({
                        status: data.status,
                        files_written: data.files_written ?? 0,
                        bytes_written: data.bytes_written ?? 0,
                        warnings: data.warnings ?? [],
                        error: data.error ?? null,
                        zip_path: data.zip_path ?? null,
                        finished_at: Date.now() / 1000,
                    });
                } catch {
                    /* fetch a fresh snapshot if the terminal frame was malformed */
                    exportApi.getJob(jobId).then(setActiveJob).catch(() => undefined);
                }
                es?.close();
                es = null;
            });

            es.onerror = () => {
                // Browser auto-retries; if the connection never opens we fall back.
                if (es && es.readyState === EventSource.CLOSED) {
                    es = null;
                    startPolling();
                }
            };
        } catch {
            startPolling();
        }

        return () => {
            cancelled = true;
            if (es) es.close();
            if (pollHandle !== null) clearInterval(pollHandle);
        };
    }, [activeJobId, activeJobInitialStatus, setActiveJob, patchJob]);

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            // Pre-flight validate so the user sees field-level errors early.
            const v = await exportApi.validate(draft);
            if (!v.success) {
                const msgs = (v.errors || [])
                    .map((e) => `${e.loc.join('.')}: ${e.msg}`)
                    .join('\n');
                message.error({ content: `Blueprint 校验失败:\n${msgs}`, duration: 8 });
                return;
            }
            const job = await exportApi.submit(draft, true);
            setActiveJob(job);
            message.success(`已提交导出任务 ${job.id}`);
        } catch (e) {
            message.error(`提交失败: ${(e as Error).message}`);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Space direction="vertical" size="middle" style={{ width: '100%', padding: 24 }}>
            <Flex justify="space-between" align="center">
                <Title level={3} style={{ margin: 0 }}>
                    📦 Blueprint 导出向导
                </Title>
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={resetDraft}>
                        重置草稿
                    </Button>
                </Space>
            </Flex>
            <Paragraph type="secondary">
                把当前平台里"装配好"的 Agent / Skill / MCP / 配置打包成可独立部署的内网交付包。
            </Paragraph>

            <Steps
                current={step}
                onChange={setStep}
                items={[
                    { title: '基础 & LLM', icon: <PlayCircleOutlined /> },
                    { title: '资产选择' },
                    { title: '预览 & 导出' },
                ]}
            />

            <Card>
                {step === 0 && <StepBasics />}
                {step === 1 && <StepAssets catalog={catalog} loading={catalogLoading} />}
                {step === 2 && (
                    <StepReview
                        onSubmit={handleSubmit}
                        submitting={submitting}
                        job={activeJob}
                    />
                )}
            </Card>

            <Flex justify="space-between">
                <Button disabled={step === 0} onClick={() => setStep(step - 1)}>
                    上一步
                </Button>
                <Button
                    type="primary"
                    disabled={step === 2}
                    onClick={() => setStep(step + 1)}
                >
                    下一步
                </Button>
            </Flex>
        </Space>
    );
};

export default ExportWizardPage;
