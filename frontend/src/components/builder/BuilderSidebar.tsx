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
    { key: "core_role", label: "核心角色定义 (Core Role)", icon: <RocketOutlined /> },
    { key: "target_user", label: "目标用户群体 (Target User)", icon: <QuestionCircleOutlined /> },
    { key: "boundary", label: "行为边界与原则 (Boundary)", icon: <SafetyOutlined /> },
    { key: "tools", label: "工具与技能绑定 (Tools/Skills)", icon: <ToolOutlined /> },
    { key: "kb_bindings", label: "知识库深度绑定 (KB Bindings)", icon: <CheckCircleFilled /> },
    { key: "tone_and_style", label: "交互语气风格 (Tone & Style)", icon: <QuestionCircleOutlined /> },
    { key: "guardrails", label: "合规安全护栏 (Guardrails)", icon: <SafetyOutlined /> },
    { key: "success_criteria", label: "业务成功准则 (Success Criteria)", icon: <LineChartOutlined /> },
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
                <Title level={5}>设计要素确立进度</Title>
                <Progress 
                    type="circle" 
                    percent={Math.round(coverage * 100)} 
                    strokeColor={{ '0%': '#108ee9', '100%': '#06D6A0' }}
                    size={120}
                    style={{ display: 'block', margin: '16px auto' }}
                />
                <Text type="secondary" style={{ fontSize: '12px', textAlign: 'center', display: 'block' }}>
                    已确立并锁定 {Math.round(coverage * 100)}% 的 Agent 核心构建维度。
                </Text>
            </Card>

            {/* 2. Dimensions Checklist */}
            <Card title="设计要素维度" bordered={false} className="glass-card">
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
            <Card title="智能匹配并召回的资产" bordered={false} className="glass-card">
                <div style={{ marginBottom: '12px' }}>
                    <Text strong style={{ fontSize: '12px' }}>绑定技能 (Skills)</Text>
                    <div style={{ marginTop: '4px' }}>
                        {discoveredContext.matched_skills?.length > 0 ? (
                            discoveredContext.matched_skills.map((s: string) => (
                                <Tag key={s} color="cyan" style={{ marginBottom: '4px' }}>{s}</Tag>
                            ))
                        ) : (
                            <Text type="secondary" italic style={{ fontSize: '12px' }}>暂未匹配到可用技能</Text>
                        )}
                    </div>
                </div>
                <div>
                    <Text strong style={{ fontSize: '12px' }}>推荐匹配模板 (Templates)</Text>
                    <div style={{ marginTop: '4px' }}>
                        {discoveredContext.matched_agents?.length > 0 ? (
                            discoveredContext.matched_agents.map((a: string) => (
                                <Tag key={a} color="purple" style={{ marginBottom: '4px' }}>{a}</Tag>
                            ))
                        ) : (
                            <Text type="secondary" italic style={{ fontSize: '12px' }}>暂无推荐模板</Text>
                        )}
                    </div>
                </div>
            </Card>
        </div>
    );
};
