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
            // Note: In a real environment, this calls the backend which runs the LangGraph
            const response = await builderApi.sendMessage(
                state.session_id,
                state.user_id,
                inputText,
                state // Pass current state for context
            );

            const serverState = response.data;
            
            // Extract the last AI message
            const aiMsgs = serverState.messages.filter((m: any) => m.type === 'ai' || m.role === 'assistant');
            const latestAiMsg = aiMsgs[aiMsgs.length - 1];

            setState({
                ...serverState,
                messages: [...newMessages, { 
                    id: Date.now() + 1, 
                    content: latestAiMsg?.content || "Processing...", 
                    role: 'assistant' 
                }]
            });
        } catch (error) {
            console.error(error);
            message.error("Failed to connect to Builder Engine.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <PageContainer
            title="Agent Builder Assistant"
            description="Co-create premium Agents using structured 6-stage interview and Eval-Driven Development (EDD)."
            extra={[
                <Button key="reset" icon={<ClearOutlined />}>Reset Session</Button>,
                <Button key="config" icon={<SettingOutlined />} type="primary">View Config</Button>
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
                                    title="Welcome to Agent Builder"
                                    description="I will help you design, test, and deploy a high-performance Agent. Let's start by defining what you want to build."
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
                            {loading && <Bubble placement="start" loading content="Thinking..." />}
                        </div>

                        <div style={{ marginTop: 'auto', paddingTop: '12px' }}>
                            <Sender
                                value={inputText}
                                onChange={setInputText}
                                onSubmit={handleSend}
                                loading={loading}
                                placeholder="Type your requirements or answer questions..."
                                prefix={<Space><Text type="secondary" style={{ fontSize: 12 }}>Round {state.interview_round}</Text></Space>}
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
