import React from 'react';
import { Card, List, Button, Tag, Space, Typography, Tooltip } from 'antd';
import { DatabaseOutlined, RightOutlined } from '@ant-design/icons';
import type { KnowledgeBase } from '../../types';

const { Text } = Typography;

interface Props {
    kbs: KnowledgeBase[];
    loading: boolean;
    onSelect: (kb: KnowledgeBase) => void;
}

export const KnowledgeList: React.FC<Props> = ({ kbs, loading, onSelect }) => {
    return (
        <List
            grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 3, xl: 4, xxl: 4 }}
            dataSource={kbs}
            loading={loading}
            renderItem={(item) => (
                <List.Item>
                    <Card
                        hoverable
                        onClick={() => onSelect(item)}
                        actions={[
                            <Button type="link" onClick={(e) => { e.stopPropagation(); onSelect(item); }}>
                                查看详情 <RightOutlined />
                            </Button>
                        ]}
                    >
                        <Card.Meta
                            avatar={<DatabaseOutlined style={{ fontSize: 24, color: 'var(--ant-color-primary)' }} />}
                            title={item.name}
                            description={
                                <div style={{ height: 60, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                                    <Text type="secondary" ellipsis={{ tooltip: item.description }}>
                                        {item.description || '暂无描述'}
                                    </Text>

                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                                        <Space size={4}>
                                            <Tag color="blue">v{item.version || 1}</Tag>
                                            {item.is_public && <Tag color="green">公开</Tag>}
                                        </Space>
                                        <Tooltip title="创建时间">
                                            <Text type="secondary" style={{ fontSize: 12 }}>
                                                {new Date(item.created_at).toLocaleDateString()}
                                            </Text>
                                        </Tooltip>
                                    </div>
                                </div>
                            }
                        />
                    </Card>
                </List.Item>
            )}
        />
    );
};
