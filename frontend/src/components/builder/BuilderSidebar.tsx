import React from 'react';
import { Card, Progress, Typography, List, Tag, Space, Badge } from 'antd';
import { 
    CheckCircleFilled, 
    QuestionCircleOutlined, 
    RocketOutlined, 
    ToolOutlined, 
    SafetyOutlined,
    LineChartOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface BuilderSidebarProps {
    coverage: number;
    confirmedFields: Record<string, any>;
    missingDimensions: string[];
    discoveredContext: Record<string, any>;
}

const CORE_DIMENSIONS = [
    { key: "core_role", label: "Core Role", icon: <RocketOutlined /> },
    { key: "target_user", label: "Target User", icon: <QuestionCircleOutlined /> },
    { key: "boundary", label: "Boundary", icon: <SafetyOutlined /> },
    { key: "tools", label: "Tools/Skills", icon: <ToolOutlined /> },
    { key: "kb_bindings", label: "KB Bindings", icon: <CheckCircleFilled /> },
    { key: "tone_and_style", label: "Tone & Style", icon: <QuestionCircleOutlined /> },
    { key: "guardrails", label: "Guardrails", icon: <SafetyOutlined /> },
    { key: "success_criteria", label: "Success Criteria", icon: <LineChartOutlined /> },
];

export const BuilderSidebar: React.FC<BuilderSidebarProps> = ({ 
    coverage, 
    confirmedFields, 
    missingDimensions,
    discoveredContext 
}) => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflowY: 'auto', paddingRight: '4px' }}>
            {/* 1. Overall Progress */}
            <Card bordered={false} className="glass-card">
                <Title level={5}>Build Progress</Title>
                <Progress 
                    type="circle" 
                    percent={Math.round(coverage * 100)} 
                    strokeColor={{ '0%': '#108ee9', '100%': '#06D6A0' }}
                    size={120}
                    style={{ display: 'block', margin: '16px auto' }}
                />
                <Text type="secondary" style={{ fontSize: '12px', textAlign: 'center', display: 'block' }}>
                    {Math.round(coverage * 100)}% of requirements locked.
                </Text>
            </Card>

            {/* 2. Dimensions Checklist */}
            <Card title="Dimensions" bordered={false} className="glass-card">
                <List
                    size="small"
                    dataSource={CORE_DIMENSIONS}
                    renderItem={(item) => {
                        const isConfirmed = !!confirmedFields[item.key];
                        return (
                            <List.Item style={{ opacity: isConfirmed ? 1 : 0.4 }}>
                                <Space>
                                    <Badge status={isConfirmed ? "success" : "default"} />
                                    {item.icon}
                                    <Text delete={isConfirmed}>{item.label}</Text>
                                </Space>
                                {isConfirmed && <CheckCircleFilled style={{ color: '#06D6A0' }} />}
                            </List.Item>
                        );
                    }}
                />
            </Card>

            {/* 3. Discovered Assets */}
            <Card title="Matched Assets" bordered={false} className="glass-card">
                <div style={{ marginBottom: '12px' }}>
                    <Text strong style={{ fontSize: '12px' }}>Skills</Text>
                    <div style={{ marginTop: '4px' }}>
                        {discoveredContext.matched_skills?.length > 0 ? (
                            discoveredContext.matched_skills.map((s: string) => (
                                <Tag key={s} color="cyan" style={{ marginBottom: '4px' }}>{s}</Tag>
                            ))
                        ) : (
                            <Text type="secondary" italic style={{ fontSize: '12px' }}>None yet</Text>
                        )}
                    </div>
                </div>
                <div>
                    <Text strong style={{ fontSize: '12px' }}>Templates</Text>
                    <div style={{ marginTop: '4px' }}>
                        {discoveredContext.matched_agents?.length > 0 ? (
                            discoveredContext.matched_agents.map((a: string) => (
                                <Tag key={a} color="purple" style={{ marginBottom: '4px' }}>{a}</Tag>
                            ))
                        ) : (
                            <Text type="secondary" italic style={{ fontSize: '12px' }}>None yet</Text>
                        )}
                    </div>
                </div>
            </Card>
        </div>
    );
};
