
import React, { useState, useRef } from 'react';
import { 
    Table, 
    Tag, 
    Typography, 
    Card, 
    Input, 
    Space, 
    Button, 
    Drawer, 
    Descriptions, 
    Flex, 
    Breadcrumb, 
    Alert,
    Empty,
    Row,
    Col,
    Tabs,
    Divider,
    Select,
    Tooltip,
    List,
    Spin,
    Avatar,
    Checkbox
} from 'antd';
import { 
    DatabaseOutlined, 
    SearchOutlined, 
    FileTextOutlined, 
    DeploymentUnitOutlined,
    InfoCircleOutlined,
    ArrowLeftOutlined,
    CodeOutlined,
    PartitionOutlined,
    DotChartOutlined,
    UnorderedListOutlined,
    FullscreenExitOutlined,
    AimOutlined,
    RobotOutlined,
    MessageOutlined,
    SendOutlined,
    UserOutlined,
    SyncOutlined,
    QuestionCircleOutlined
} from '@ant-design/icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { GraphVisualizer } from '../components/knowledge/GraphVisualizer';
import type { GraphVisualizerHandle } from '../components/knowledge/GraphVisualizer';

const { Title, Text, Paragraph } = Typography;

const NODE_COLORS: Record<string, string> = {
    'Requirement': '#1890ff',
    'Design': '#722ed1',
    'File': '#06D6A0',
    'CodeEntity': '#FA8C16',
    'Person': '#FADB14',
    'Commit': '#13C2C2',
    'Rule': '#B37FEB',
    'Comment': '#FF85C0',
    'Task': '#EB2F96',
    'Incident': '#FF4D4F',
    'Unknown': '#595959'
};

export const ArchitectureAssetsPage: React.FC = () => {
    const navigate = useNavigate();
    const [searchText, setSearchText] = useState('');
    const [selectedAsset, setSelectedAsset] = useState<any>(null);
    const [activeTab, setActiveTab] = useState('list');
    const visualizerRef = useRef<GraphVisualizerHandle>(null);
    
    // 🧠 [Oracle Intelligence]: 架构智体状态
    const [oracleOpen, setOracleOpen] = useState(false);
    const [oracleQuery, setOracleQuery] = useState('');
    const [oracleMessages, setOracleMessages] = useState<any[]>([]);
    const [askingOracle, setAskingOracle] = useState(false);
    const [excludedNodeTypes, setExcludedNodeTypes] = useState<string[]>(['CodeEntity']);

    const askOracle = async () => {
        if (!oracleQuery.trim()) return;
        
        const userMsg = { role: 'user', content: oracleQuery };
        setOracleMessages(prev => [...prev, userMsg]);
        setOracleQuery('');
        setAskingOracle(true);

        try {
            const res = await api.post('/governance/oracle', { 
                query: oracleQuery,
                context: {
                    page: 'ArchitectureAssets',
                    selected_asset_id: selectedAsset?.id
                }
            });
            const botMsg = { 
                role: 'assistant', 
                content: res.data.data.answer,
                cypher: res.data.data.cypher
            };
            setOracleMessages(prev => [...prev, botMsg]);
        } catch (e) {
            setOracleMessages(prev => [...prev, { role: 'assistant', content: '抱歉，智体暂时无法理解此架构问题。', error: true }]);
        } finally {
            setAskingOracle(false);
        }
    };

    const handleSuggestedQuery = (query: string) => {
        setOracleQuery(query);
    };

    const { data: assets, isLoading: loadingList } = useQuery({
        queryKey: ['architecture-assets'],
        queryFn: async () => {
            const res = await api.get('/governance/assets');
            return res.data.data;
        }
    });

    const { data: graphData, isLoading: loadingGraph } = useQuery({
        queryKey: ['architecture-graph'],
        queryFn: async () => {
            const res = await api.get('/governance/graph');
            return res.data.data;
        },
        enabled: activeTab === 'graph'
    });

    const filteredAssets = assets?.filter((asset: any) => 
        (asset.name || '').toLowerCase().includes(searchText.toLowerCase()) ||
        (asset.path || '').toLowerCase().includes(searchText.toLowerCase()) ||
        (asset.type || '').toLowerCase().includes(searchText.toLowerCase())
    );

    const columns = [
        {
            title: '资产名称',
            dataIndex: 'name',
            key: 'name',
            render: (text: string, record: any) => (
                <Space>
                    {record.type === 'Requirement' ? <FileTextOutlined style={{ color: '#1890ff' }} /> : 
                     record.type === 'Design' ? <DeploymentUnitOutlined style={{ color: '#722ed1' }} /> : 
                     <CodeOutlined style={{ color: '#06D6A0' }} />}
                    <Text strong style={{ color: '#fff' }}>{text}</Text>
                </Space>
            ),
        },
        {
            title: '类型',
            dataIndex: 'type',
            key: 'type',
            render: (type: string) => (
                <Tag color={NODE_COLORS[type] || 'default'}>
                    {type}
                </Tag>
            ),
        },
        {
            title: '物理路径',
            dataIndex: 'path',
            key: 'path',
            render: (path: string) => <Text code style={{ fontSize: 11, background: '#1f1f1f', color: '#8c8c8c' }}>{path}</Text>,
        },
        {
            title: '同步时间',
            dataIndex: 'time',
            key: 'time',
            render: (time: string) => <Text type="secondary" style={{ fontSize: 12 }}>{time}</Text>,
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: any) => (
                <Button type="link" onClick={() => setSelectedAsset(record)}>详情</Button>
            ),
        },
    ];

    const handleQuickSearch = (nodeId: string) => {
        visualizerRef.current?.zoomToNode(nodeId);
        // 同步打开详情侧边栏
        const asset = assets?.find((a: any) => a.id === nodeId);
        if (asset) setSelectedAsset(asset);
    };

    const renderGraphView = () => {
        if (!graphData) return <Empty description="无法加载图谱数据" />;

        const filteredNodes = (graphData.nodes || []).filter((n: any) => !excludedNodeTypes.includes(n.group));
        const nodeIds = new Set(filteredNodes.map((n: any) => n.id));
        const filteredLinks = (graphData.links || []).filter((l: any) => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            return nodeIds.has(sourceId) && nodeIds.has(targetId);
        });

        const enrichedGraph = {
            nodes: filteredNodes.map((n: any) => ({
                ...n,
                color: NODE_COLORS[n.group] || '#595959',
                val: n.group === 'File' ? 4 : 7
            })),
            links: filteredLinks
        };

        return (
            <Card 
                bordered={false} 
                bodyStyle={{ padding: 0, overflow: 'hidden', height: '640px', position: 'relative' }}
                style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}
            >
                {/* 🔍 [Navigation Overlay] */}
                <div style={{ position: 'absolute', top: 20, right: 20, zIndex: 10, display: 'flex', gap: 12 }}>
                    <Select
                        showSearch
                        placeholder="快捷定位资产节点..."
                        optionFilterProp="children"
                        onChange={handleQuickSearch}
                        style={{ width: 260 }}
                        dropdownStyle={{ background: '#1f1f1f', border: '1px solid #444' }}
                    >
                        {graphData?.nodes.map((n: any) => (
                            <Select.Option key={n.id} value={n.id}>
                                <span style={{ color: NODE_COLORS[n.group], marginRight: 8 }}>●</span>
                                <span style={{ color: '#fff' }}>{n.name}</span>
                                <small style={{ color: '#595959', marginLeft: 8 }}>({n.group})</small>
                            </Select.Option>
                        ))}
                    </Select>

                    <Tooltip title="重置视角 (Fit to screen)">
                        <Button 
                            icon={<FullscreenExitOutlined />} 
                            onClick={() => visualizerRef.current?.resetZoom()} 
                            style={{ background: '#262626', borderColor: '#444', color: '#fff' }}
                        />
                    </Tooltip>

                    <Tooltip title="询问架构智体 (Architecture Oracle)">
                        <Button 
                            type="primary"
                            icon={<RobotOutlined />} 
                            onClick={() => setOracleOpen(true)} 
                            style={{ background: '#722ed1', borderColor: '#722ed1' }}
                        >
                            Oracle
                        </Button>
                    </Tooltip>
                </div>

                <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, background: 'rgba(0,0,0,0.6)', padding: 12, borderRadius: 8, border: '1px solid #444' }}>
                    <Checkbox.Group 
                        value={Object.keys(NODE_COLORS).filter(t => !excludedNodeTypes.includes(t) && t !== 'Unknown')}
                        onChange={(checked) => {
                            const allTypes = Object.keys(NODE_COLORS).filter(t => t !== 'Unknown');
                            setExcludedNodeTypes(allTypes.filter(t => !checked.includes(t)));
                        }}
                        style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
                    >
                        {['Requirement', 'Design', 'File', 'CodeEntity', 'Commit', 'Rule', 'Incident'].map((type) => (
                            <Checkbox key={type} value={type} style={{ margin: 0, color: '#d9d9d9', fontSize: 12 }}>
                                <span style={{ color: NODE_COLORS[type], marginRight: 8 }}>●</span>
                                {type}
                            </Checkbox>
                        ))}
                    </Checkbox.Group>
                    <Divider style={{ margin: '12px 0', borderColor: '#444' }} />
                    <div style={{ maxWidth: 160 }}>
                        <Text type="secondary" style={{ fontSize: 10, display: 'block', marginBottom: 4 }}>
                            <AimOutlined /> <b>左键</b>: 旋转/移动详情
                        </Text>
                        <Text type="secondary" style={{ fontSize: 10, display: 'block', marginBottom: 4 }}>
                            <PartitionOutlined /> <b>滚轮</b>: 缩放画布
                        </Text>
                        <Text type="secondary" style={{ fontSize: 10, display: 'block' }}>
                            <CodeOutlined /> <b>点击</b>: 聚焦节点并查看代码详情
                        </Text>
                    </div>
                </div>

                {loadingGraph ? (
                    <Flex align="center" justify="center" style={{ height: '100%' }}>
                        <PartitionOutlined spin style={{ fontSize: 32, color: '#1890ff' }} />
                        <Text style={{ marginLeft: 12, color: '#8c8c8c' }}>正在构建架构拓扑图...</Text>
                    </Flex>
                ) : enrichedGraph ? (
                    <GraphVisualizer
                        ref={visualizerRef}
                        data={enrichedGraph}
                        onNodeClick={(node: any) => {
                            const asset = assets?.find((a: any) => a.id === node.id);
                            if (asset) {
                                visualizerRef.current?.zoomToNode(node.id);
                                setSelectedAsset(asset);
                            }
                        }}
                    />
                ) : (
                    <Empty description="无法加载图谱数据" />
                )}
            </Card>
        );
    };

    return (
        <div style={{ padding: 24, background: '#0a0a0a', minHeight: '100%', color: '#fff' }}>
            <Flex vertical gap={24}>
                <Flex align="center" gap={16}>
                    <Button 
                        icon={<ArrowLeftOutlined />} 
                        onClick={() => navigate('/devGovernance')}
                        style={{ background: 'transparent', color: '#8c8c8c', border: '1px solid #303030' }}
                    />
                    <div>
                        <Breadcrumb items={[
                            { title: <Text style={{ color: '#8c8c8c' }}>研发治理</Text> },
                            { title: <Text style={{ color: '#fff' }}>架构资产明细柜</Text> }
                        ]} />
                        <Title level={2} style={{ color: '#fff', margin: '4px 0 0 0' }}>架构资产明细 (Asset Registry)</Title>
                    </div>
                </Flex>

                <Alert
                    message="知识图谱资产说明"
                    description={
                        <Space direction="vertical" size={2}>
                            <Text style={{ color: 'rgba(255,255,255,0.85)' }}>所有的架构资产均由 L5 治理智体从物理项目库中自动提取并注册至 Neo4j。这些资产构成了 HiveMind 的“数字孪生”认知基础。</Text>
                        </Space>
                    }
                    type="info"
                    showIcon
                    icon={<InfoCircleOutlined />}
                    style={{ background: 'rgba(24, 144, 255, 0.05)', border: '1px solid #164c7e', borderRadius: 12 }}
                />

                <Tabs 
                    activeKey={activeTab} 
                    onChange={setActiveTab}
                    className="custom-tabs"
                    items={[
                        {
                            key: 'list',
                            label: <span><UnorderedListOutlined /> 资产列表清单</span>,
                            children: (
                                <Card 
                                    bordered={false} 
                                    style={{ background: '#141414', borderRadius: 12, border: '1px solid #303030' }}
                                    bodyStyle={{ padding: 0 }}
                                >
                                    <div style={{ padding: '16px 24px', borderBottom: '1px solid #303030' }}>
                                        <Input
                                            placeholder="搜索资产名称、类型或路径..."
                                            prefix={<SearchOutlined style={{ color: '#595959' }} />}
                                            value={searchText}
                                            onChange={e => setSearchText(e.target.value)}
                                            style={{ maxWidth: 400, background: '#1f1f1f', border: 'none', color: '#fff' }}
                                        />
                                    </div>
                                    <Table 
                                        dataSource={filteredAssets} 
                                        columns={columns} 
                                        rowKey="id"
                                        loading={loadingList}
                                        pagination={{ pageSize: 12, size: 'small' }}
                                        style={{ background: '#141414' }}
                                        className="custom-table"
                                        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未发现匹配资产" /> }}
                                    />
                                </Card>
                            )
                        },
                        {
                            key: 'graph',
                            label: <span><DotChartOutlined /> 架构关联拓扑</span>,
                            children: renderGraphView()
                        }
                    ]}
                />

                <Card 
                    title={<span style={{ color: '#fff' }}><InfoCircleOutlined /> 治理资产指南 (Governance Guide)</span>}
                    bordered={false} 
                    style={{ background: 'rgba(24, 144, 255, 0.02)', borderRadius: 12, border: '1px dashed #303030' }}
                >
                    <Row gutter={48}>
                        <Col span={8}>
                            <Title level={5} style={{ color: NODE_COLORS['File'] }}>01. File (代码资产)</Title>
                            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
                                物理代码文件节点。它们是图谱中的叶子节点，承载着业务逻辑的最终实现。
                            </Paragraph>
                        </Col>
                        <Col span={8}>
                            <Title level={5} style={{ color: NODE_COLORS['Requirement'] }}>02. Requirement (需求语义)</Title>
                            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
                                定义“系统应当做什么”的语义节点。通过 `IMPLEMENTED_BY` 映射到代码实现。
                            </Paragraph>
                        </Col>
                        <Col span={8}>
                            <Title level={5} style={{ color: NODE_COLORS['Commit'] }}>03. Commit & Person (工程回溯)</Title>
                            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
                                自动同步的 Git 提交记录与贡献者。建立了“谁在什么时候修改了什么”的责任链路。
                            </Paragraph>
                        </Col>
                        <Col span={8}>
                            <Title level={5} style={{ color: NODE_COLORS['Rule'] }}>04. Rule (研发规约)</Title>
                            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
                                项目内置的规则文档。它们是治理哨兵执行审计任务时的法律依据。
                            </Paragraph>
                        </Col>
                        <Col span={8}>
                            <Title level={5} style={{ color: NODE_COLORS['Comment'] }}>05. Comment (注释/TODO)</Title>
                            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
                                从源码中提取的 `TODO` 或 `FIXME`。作为“治理碎屑”，被自动汇聚入图。
                            </Paragraph>
                        </Col>
                        <Col span={8}>
                            <Title level={5} style={{ color: NODE_COLORS['Design'] }}>06. Design (架构决策)</Title>
                            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
                                架构设计文档节点。连接需求与代码的中轴，是防止“架构漂移”的核心观测点。
                            </Paragraph>
                        </Col>
                    </Row>
                </Card>
            </Flex>

            <Drawer
                title={<span style={{ color: '#fff' }}><DatabaseOutlined /> 资产元数据详情</span>}
                placement="right"
                onClose={() => setSelectedAsset(null)}
                open={!!selectedAsset}
                width={500}
                headerStyle={{ background: '#141414', borderBottom: '1px solid #303030' }}
                bodyStyle={{ background: '#0f0f0f', color: '#fff' }}
            >
                {selectedAsset && (
                    <Space direction="vertical" size={24} style={{ width: '100%' }}>
                        <Card style={{ background: '#1a1a1a', border: '1px solid #333' }}>
                            <Descriptions column={1} labelStyle={{ color: '#8c8c8c' }} contentStyle={{ color: '#fff' }}>
                                <Descriptions.Item label="资产唯一标识 (ID)">
                                    <Text copyable style={{ color: '#06D6A0' }}>{selectedAsset.id}</Text>
                                </Descriptions.Item>
                                <Descriptions.Item label="资产分类">
                                    <Tag color={NODE_COLORS[selectedAsset.type] || 'blue'}>{selectedAsset.type}</Tag>
                                </Descriptions.Item>
                                <Descriptions.Item label="最后同步时间">
                                    {selectedAsset.time}
                                </Descriptions.Item>
                            </Descriptions>
                        </Card>

                        <div>
                            <Title level={5} style={{ color: '#8c8c8c' }}><FileTextOutlined /> 语义摘要 (Summary)</Title>
                            <Paragraph style={{ color: 'rgba(255,255,255,0.85)', background: '#1a1a1a', padding: 16, borderRadius: 8 }}>
                                {selectedAsset.summary}
                            </Paragraph>
                        </div>

                        <div>
                            <Title level={5} style={{ color: '#8c8c8c' }}><PartitionOutlined /> 关联链路 (Links)</Title>
                            <Alert
                                message={`此资产正在图谱中保持 Active 状态`}
                                type="success"
                                showIcon
                                style={{ background: 'rgba(82, 196, 26, 0.05)', border: '1px solid #237804' }}
                            />
                        </div>
                    </Space>
                )}
            </Drawer>

            <style>{`
                .custom-tabs .ant-tabs-nav::before {
                    border-bottom: 1px solid #303030 !important;
                }
                .custom-tabs .ant-tabs-tab {
                    color: #8c8c8c !important;
                }
                .custom-tabs .ant-tabs-tab-active .ant-tabs-tab-btn {
                    color: #06D6A0 !important;
                }
                .custom-tabs .ant-tabs-ink-bar {
                    background: #06D6A0 !important;
                }
                .custom-table .ant-table {
                    background: transparent !important;
                }
                .custom-table .ant-table-thead > tr > th {
                    background: #1a1a1a !important;
                    color: #8c8c8c !important;
                    border-bottom: 1px solid #303030 !important;
                }
                .custom-table .ant-table-tbody > tr > td {
                    border-bottom: 1px solid #1f1f1f !important;
                }
                .custom-table .ant-table-tbody > tr:hover > td {
                    background: rgba(255, 255, 255, 0.02) !important;
                }
                .ant-pagination-item {
                    background: #141414 !important;
                    border-color: #303030 !important;
                }
                .ant-pagination-item-active {
                    border-color: #06D6A0 !important;
                }
                .ant-pagination-item-active a {
                    color: #06D6A0 !important;
                }
            `}</style>

            {/* 🧠 [Oracle Drawer]: 架构智体交互界面 */}
            <Drawer
                title={<span style={{ color: '#fff' }}><RobotOutlined /> 架构智体口谕 (Oracle Insights)</span>}
                placement="right"
                onClose={() => setOracleOpen(false)}
                open={oracleOpen}
                width={480}
                headerStyle={{ background: '#1f1f1f', borderBottom: '1px solid #303030' }}
                bodyStyle={{ background: '#141414', padding: 0, display: 'flex', flexDirection: 'column' }}
            >
                <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>
                    <List
                        dataSource={oracleMessages}
                        renderItem={(item) => (
                            <List.Item style={{ border: 'none', padding: '12px 0' }}>
                                <List.Item.Meta
                                    avatar={<Avatar icon={item.role === 'user' ? <UserOutlined /> : <RobotOutlined />} style={{ background: item.role === 'user' ? '#1890ff' : '#722ed1' }} />}
                                    title={<Text style={{ color: item.role === 'user' ? '#1890ff' : '#9254de', fontWeight: 'bold' }}>{item.role === 'user' ? 'You' : 'Oracle'}</Text>}
                                    description={
                                        <div style={{ background: '#1f1f1f', padding: 12, borderRadius: 8, color: '#d9d9d9', border: '1px solid #303030' }}>
                                            {item.content}
                                            {item.cypher && (
                                                <div style={{ marginTop: 12, borderRadius: 4, overflow: 'hidden' }}>
                                                    <Text type="secondary" style={{ fontSize: 10, display: 'block', marginBottom: 4, paddingLeft: 8 }}>Generated Cypher (Traceable):</Text>
                                                    <SyntaxHighlighter 
                                                        language="cypher" 
                                                        style={atomDark}
                                                        customStyle={{ margin: 0, fontSize: 10, padding: 8 }}
                                                    >
                                                        {item.cypher}
                                                    </SyntaxHighlighter>
                                                </div>
                                            )}
                                        </div>
                                    }
                                />
                            </List.Item>
                        )}
                    />
                    {askingOracle && (
                        <Flex align="center" gap={8} style={{ padding: '12px 0' }}>
                            <Spin size="small" />
                            <Text type="secondary">智体正在检索 Neo4j 拓扑并进行语义对账...</Text>
                        </Flex>
                    )}
                    {oracleMessages.length === 0 && (
                        <div style={{ textAlign: 'center', marginTop: 100 }}>
                            <MessageOutlined style={{ fontSize: 48, color: '#303030', marginBottom: 24 }} />
                            <Title level={5} style={{ color: '#fff' }}>由于您是首次与其对话</Title>
                            <Text type="secondary">我是架构智体 Oracle，您可以询问我关于此仓库的任何拓扑与关联问题。</Text>
                            
                            <Flex vertical gap={12} style={{ marginTop: 32 }}>
                                {[
                                    "谁开发的 backend/app/agents/swarm.py 模块？",
                                    "哪个文件被引用次数最多？",
                                    "系统有哪些治理事故尚未解决？"
                                ].map((q, idx) => (
                                    <Button 
                                        key={idx}
                                        icon={<QuestionCircleOutlined />}
                                        style={{ background: '#1a1a1a', border: '1px solid #303030', color: '#1890ff', textAlign: 'left' }}
                                        onClick={() => handleSuggestedQuery(q)}
                                    >
                                        {q}
                                    </Button>
                                ))}
                            </Flex>
                        </div>
                    )}
                </div>
                <div style={{ padding: 16, background: '#1f1f1f', borderTop: '1px solid #303030' }}>
                    <Input.Search
                        placeholder="输入您的架构疑问..."
                        enterButton={<SendOutlined />}
                        loading={askingOracle}
                        value={oracleQuery}
                        onChange={e => setOracleQuery(e.target.value)}
                        onSearch={askOracle}
                        style={{ background: '#141414' }}
                        disabled={askingOracle}
                    />
                </div>
            </Drawer>
        </div>
    );
};
