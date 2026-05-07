import React, { useState, useEffect, useRef } from 'react';
import { Layout, Typography, Card, Button, Space, App as AntApp } from 'antd';
import { Bubble, Welcome, Sender } from '@ant-design/x';
import { RocketOutlined, ClearOutlined, SettingOutlined } from '@ant-design/icons';
import { PageContainer } from '../components/common/PageContainer';
import { BuilderSidebar } from '../components/builder/BuilderSidebar';
import { builderApi } from '../services/builderApi';
import type { BuilderState } from '../services/builderApi';

const { Content, Sider } = Layout;
const { Title, Text } = Typography;

export const AgentBuilderPage: React.FC = () => {
    const { message } = AntApp.useApp();
    const [loading, setLoading] = useState(false);
    const [inputText, setInputText] = useState('');
    const [state, setState] = useState<BuilderState>({
        session_id: `session_${Math.random().toString(36).substr(2, 9)}`,
        user_id: 'user_123',
        messages: [],
        confirmed_fields: {},
        missing_dimensions: [],
        coverage_pct: 0,
        discovered_context: {},
        research_insights: [],
        added_features_count: 0,
        scope_warning: null,
        golden_dataset: [],
        generated_config: null,
        interview_round: 0,
        next_step: 'interview'
    });

    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [state.messages]);

    const handleSend = async () => {
        if (!inputText.trim() || loading) return;

        const userMsg = {
            id: Date.now().toString(),
            content: inputText,
            role: 'user',
            type: 'human'
        };

        const newMessages = [...state.messages, userMsg];
        setState(prev => ({ ...prev, messages: newMessages }));
        setInputText('');
        setLoading(true);

        try {
            const response = await builderApi.sendMessage(
                state.session_id,
                state.user_id,
                inputText,
                state
            );

            const serverState = response.data;
            const aiMsgs = serverState.messages.filter((m: any) => m.type === 'ai' || m.role === 'assistant');
            const latestAiMsg = aiMsgs[aiMsgs.length - 1];

            setState({
                ...serverState,
                messages: [...newMessages, { 
                    id: Date.now() + 1, 
                    content: latestAiMsg?.content || "智能生成中...", 
                    role: 'assistant' 
                }]
            });
        } catch (error) {
            console.error(error);
            message.error("连接智能体构建引擎失败，请检查服务。");
        } finally {
            setLoading(false);
        }
    };

    return (
        <PageContainer
            title="Agent 智能体构建助手 (Agent Builder)"
            description="通过结构化的 6 阶段人机协同访谈与评估驱动开发（EDD），轻而易举设计并构建出符合业务高标准的 Agent 智能体。"
            extra={[
                <Button key="reset" icon={<ClearOutlined />}>重置会话</Button>,
                <Button key="config" icon={<SettingOutlined />} type="primary">查看配置</Button>
            ]}
        >
            <Layout style={{ background: 'transparent', height: 'calc(100vh - 180px)' }}>
                <Content style={{ display: 'flex', flexDirection: 'column', paddingRight: '24px' }}>
                    <Card 
                        bordered={false} 
                        className="glass-card" 
                        style={{ flex: 1, display: 'flex', flexDirection: 'column', marginBottom: '16px', overflow: 'hidden' }}
                        bodyStyle={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '12px' }}
                    >
                        <div 
                            ref={scrollRef}
                            style={{ flex: 1, overflowY: 'auto', padding: '10px' }}
                        >
                            {state.messages.length === 0 ? (
                                <Welcome
                                    icon={<RocketOutlined style={{ fontSize: 40, color: '#06D6A0' }} />}
                                    title="欢迎来到 Agent 智能体构建助手"
                                    description="我是您的智能体共创助手。我将通过对话式引导您完成智能体的需求分析、功能定义、工具绑定与评测集设计。让我们从输入您想要构建的智能体目标开始吧！"
                                />
                            ) : (
                                state.messages.map((msg, i) => (
                                    <Bubble
                                        key={i}
                                        placement={msg.role === 'user' ? 'end' : 'start'}
                                        content={msg.content}
                                        avatar={{ 
                                            icon: msg.role === 'user' ? undefined : <RocketOutlined />,
                                            style: { backgroundColor: msg.role === 'user' ? '#118AB2' : '#06D6A0' }
                                        }}
                                    />
                                ))
                            )}
                            {loading && <Bubble placement="start" loading content="正在深度思考中..." />}
                        </div>

                        <div style={{ marginTop: 'auto', paddingTop: '12px' }}>
                            <Sender
                                value={inputText}
                                onChange={setInputText}
                                onSubmit={handleSend}
                                loading={loading}
                                placeholder="请输入您的需求或回答上面的问题..."
                                prefix={<Space><Text type="secondary" style={{ fontSize: 12 }}>第 {state.interview_round} 轮访谈</Text></Space>}
                            />
                        </div>
                    </Card>
                </Content>

                <Sider width={320} style={{ background: 'transparent' }}>
                    <BuilderSidebar 
                        coverage={state.coverage_pct}
                        confirmedFields={state.confirmed_fields}
                        missingDimensions={state.missing_dimensions}
                        discoveredContext={state.discovered_context}
                    />
                </Sider>
            </Layout>
        </PageContainer>
    );
};
