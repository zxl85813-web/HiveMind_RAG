/**
 * SettingsPage — 系统设置页面。
 *
 * 使用通用组件: PageContainer
 *
 * @module pages
 * @see REGISTRY.md > 前端 > 页面 > SettingsPage
 */

import React from 'react';
import { Card, Form, Select, Switch, Input, Typography } from 'antd';
import { PageContainer } from '../components/common';

const { Text } = Typography;

export const SettingsPage: React.FC = () => {
    return (
        <PageContainer
            title="系统设置"
            description="配置 LLM 模型、Agent 行为和系统偏好"
            maxWidth={720}
        >
            {/* LLM 设置 */}
            <Card title="🤖 LLM 模型设置">
                <Form layout="vertical">
                    <Form.Item label="默认对话模型">
                        <Select
                            defaultValue="gpt-4o-mini"
                            options={[
                                { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                                { value: 'gpt-4o', label: 'GPT-4o' },
                                { value: 'deepseek-v3', label: 'DeepSeek V3' },
                                { value: 'deepseek-r1', label: 'DeepSeek R1 (推理)' },
                                { value: 'qwen-turbo', label: '通义千问 Turbo' },
                            ]}
                        />
                    </Form.Item>
                    <Form.Item label="默认推理模型">
                        <Select
                            defaultValue="deepseek-r1"
                            options={[
                                { value: 'deepseek-r1', label: 'DeepSeek R1' },
                                { value: 'gpt-4o', label: 'GPT-4o' },
                            ]}
                        />
                    </Form.Item>
                </Form>
            </Card>

            {/* Agent 设置 */}
            <Card title="🐝 Agent 行为">
                <Form layout="vertical">
                    <Form.Item label="自省模式">
                        <Switch defaultChecked />
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                            Agent 会在回答后自动进行质量评估
                        </Text>
                    </Form.Item>
                    <Form.Item label="主动建议">
                        <Switch defaultChecked />
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                            AI 助手会主动推送相关建议和提醒
                        </Text>
                    </Form.Item>
                </Form>
            </Card>

            {/* API Key */}
            <Card title="🔑 API 密钥">
                <Form layout="vertical">
                    <Form.Item label="OpenAI API Key">
                        <Input.Password placeholder="sk-..." />
                    </Form.Item>
                    <Form.Item label="DeepSeek API Key">
                        <Input.Password placeholder="sk-..." />
                    </Form.Item>
                </Form>
            </Card>
        </PageContainer>
    );
};
