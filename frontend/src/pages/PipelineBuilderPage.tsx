import React, { useState, useCallback } from 'react';
import {
    ReactFlow,
    ReactFlowProvider,
    Background,
    applyNodeChanges,
    applyEdgeChanges,
    addEdge,
    MiniMap,
    Panel,
    useReactFlow,
} from '@xyflow/react';
import type {
    NodeChange,
    EdgeChange,
    Connection,
    Edge,
    Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Button, Card, Flex, Select, Typography, message, Tag, Layout, Drawer, Form, Input, InputNumber, Switch } from 'antd';
import { SaveOutlined, PlayCircleOutlined, SettingOutlined } from '@ant-design/icons';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

const initialNodes: Node[] = [
    {
        id: '1',
        type: 'input',
        data: { label: 'Input Document' },
        position: { x: 250, y: 50 },
        style: { background: 'var(--hm-color-primary)', color: 'white', borderRadius: 8, padding: 10, border: 'none' },
    },
    {
        id: '2',
        type: 'default',
        data: { label: 'Office/PDF Parser' },
        position: { x: 250, y: 150 },
        style: { background: 'var(--hm-color-surface)', color: 'white', borderRadius: 8, padding: 10, border: '1px solid var(--hm-color-border)' },
    },
    {
        id: '3',
        type: 'default',
        data: { label: 'Desensitization (脱敏)' },
        position: { x: 250, y: 250 },
        style: { background: 'var(--hm-color-warning)', color: 'white', borderRadius: 8, padding: 10, border: 'none' },
    },
    {
        id: '4',
        type: 'default',
        data: { label: 'Recursive Chunking' },
        position: { x: 250, y: 350 },
        style: { background: 'var(--hm-color-info)', color: 'white', borderRadius: 8, padding: 10, border: 'none' },
    },
    {
        id: '5',
        type: 'output',
        data: { label: 'Chroma Vector Store' },
        position: { x: 250, y: 450 },
        style: { background: 'var(--hm-color-success)', color: 'white', borderRadius: 8, padding: 10, border: 'none' },
    }
];

const initialEdges: Edge[] = [
    { id: 'e1-2', source: '1', target: '2', type: 'smoothstep', animated: true, style: { stroke: '#1890ff', strokeWidth: 2 } },
    { id: 'e2-3', source: '2', target: '3', type: 'smoothstep', animated: true, style: { stroke: '#1890ff', strokeWidth: 2 } },
    { id: 'e3-4', source: '3', target: '4', type: 'smoothstep', animated: true, style: { stroke: '#1890ff', strokeWidth: 2 } },
    { id: 'e4-5', source: '4', target: '5', type: 'smoothstep', animated: true, style: { stroke: '#1890ff', strokeWidth: 2 } },
];

let id = 10;
const getId = () => `dndnode_${id++}`;

const Sidebar = ({ pipelineType }: { pipelineType: string }) => {
    const onDragStart = (event: React.DragEvent, nodeType: string, label: string, color: string) => {
        event.dataTransfer.setData('application/reactflow/type', nodeType);
        event.dataTransfer.setData('application/reactflow/label', label);
        event.dataTransfer.setData('application/reactflow/color', color);
        event.dataTransfer.effectAllowed = 'move';
    };

    const ingestionNodeTypes = [
        { type: 'default', label: 'Office/PDF Parser', color: 'var(--hm-color-surface)' },
        { type: 'default', label: 'MinerU Parser (Advanced)', color: 'var(--hm-color-surface)' },
        { type: 'default', label: 'Desensitization (脱敏)', color: 'var(--hm-color-warning)' },
        { type: 'default', label: 'Recursive Chunking', color: 'var(--hm-color-info)' },
        { type: 'default', label: 'Semantic Chunking', color: 'var(--hm-color-info)' },
        { type: 'default', label: 'Intent Classification', color: 'var(--hm-color-info)' },
        { type: 'output', label: 'Chroma Vector Store', color: 'var(--hm-color-success)' },
        { type: 'output', label: 'Neo4j Graph Store', color: 'var(--hm-color-success)' },
    ];

    const retrievalNodeTypes = [
        { type: 'input', label: 'Input Query', color: 'var(--hm-color-primary)' },
        { type: 'default', label: 'Query Rewrite (HyDE)', color: 'var(--hm-color-info)' },
        { type: 'default', label: 'Knowledge Base Router', color: 'var(--hm-color-info)' },
        { type: 'default', label: 'Vector Search', color: 'var(--hm-color-warning)' },
        { type: 'default', label: 'Graph Search (GraphRAG)', color: 'var(--hm-color-warning)' },
        { type: 'default', label: 'Cross-Encoder Reranker', color: 'var(--hm-color-warning)' },
        { type: 'default', label: 'Prompt Builder', color: 'var(--hm-color-surface)' },
        { type: 'output', label: 'LLM Generator', color: 'var(--hm-color-success)' },
    ];

    const nodeTypes = pipelineType === 'ingestion' ? ingestionNodeTypes : retrievalNodeTypes;

    return (
        <aside style={{ padding: 16, background: 'var(--hm-color-bg-base)', borderRight: '1px solid var(--hm-color-border)', height: '100%', overflowY: 'auto' }}>
            <Title level={5} style={{ marginBottom: 16, color: 'var(--hm-color-text)' }}>🛠️ Components Box</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16, fontSize: 13 }}>Custom plugins & processors.<br />Drag nodes to the canvas.</Text>

            <Flex vertical gap={12}>
                {nodeTypes.map(nt => (
                    <div
                        key={nt.label}
                        onDragStart={(event) => onDragStart(event, nt.type, nt.label, nt.color)}
                        draggable
                        style={{
                            padding: '10px 12px',
                            border: `1px solid ${nt.color === 'var(--hm-color-surface)' ? 'var(--hm-color-border)' : 'transparent'}`,
                            borderRadius: 6,
                            background: nt.color,
                            color: 'white',
                            cursor: 'grab',
                            fontSize: 13,
                        }}
                    >
                        {nt.label}
                    </div>
                ))}
            </Flex>
        </aside>
    );
};

const DnDFlow = () => {
    const [nodes, setNodes] = useState<Node[]>(initialNodes);
    const [edges, setEdges] = useState<Edge[]>(initialEdges);
    const [pipelineType, setPipelineType] = useState('ingestion');
    const { screenToFlowPosition } = useReactFlow();

    // Config Drawer State
    const [configVisible, setConfigVisible] = useState(false);
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);
    const [form] = Form.useForm();

    const onNodesChange = useCallback(
        (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
        []
    );
    const onEdgesChange = useCallback(
        (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
        []
    );
    const onConnect = useCallback(
        (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
        []
    );

    const onEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
        // Simple feature to let users easily delete edges
        setEdges(eds => eds.filter(e => e.id !== edge.id));
        message.info("Edge removed. You can now connect your new nodes!");
    }, []);

    const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
        setSelectedNode(node);
        const nodeData = node.data as { config?: Record<string, unknown>; label: string };
        form.setFieldsValue(nodeData.config || {});
        setConfigVisible(true);
    }, [form]);

    const handleSaveConfig = () => {
        if (!selectedNode) return;
        const values = form.getFieldsValue();
        setNodes(nds => nds.map(n => {
            if (n.id === selectedNode.id) {
                return { ...n, data: { ...n.data, config: values } };
            }
            return n;
        }));
        setConfigVisible(false);
        message.success("Node configuration updated.");
    };

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            const type = event.dataTransfer.getData('application/reactflow/type');
            const label = event.dataTransfer.getData('application/reactflow/label');
            const color = event.dataTransfer.getData('application/reactflow/color');

            if (typeof type === 'undefined' || !type) {
                return;
            }

            const position = screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode: Node = {
                id: getId(),
                type,
                position,
                data: { label },
                style: {
                    background: color,
                    color: 'white',
                    borderRadius: 8,
                    padding: 10,
                    border: color === 'var(--hm-color-surface)' ? '1px solid var(--hm-color-border)' : 'none'
                }
            };

            setNodes((nds) => nds.concat(newNode));
        },
        [screenToFlowPosition],
    );

    const handleSave = () => {
        message.success("Pipeline config saved!");
        console.log("Saved Graph:", { nodes, edges, type: pipelineType });
    };

    return (
        <Layout style={{ height: 'calc(100vh - 120px)', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--hm-color-border)' }}>
            <Sider width={280} theme="light" style={{ background: 'var(--hm-color-bg-base)' }}>
                <Sidebar pipelineType={pipelineType} />
            </Sider>
            <Content style={{ position: 'relative' }}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onNodeClick={onNodeClick}
                    onEdgeClick={onEdgeClick}
                    defaultEdgeOptions={{
                        type: 'smoothstep',
                        animated: true,
                        style: { stroke: '#1890ff', strokeWidth: 2 }
                    }}
                    fitView
                >
                    <Background color="#ccc" gap={16} />
                    <MiniMap nodeStrokeWidth={3} zoomable pannable style={{ background: 'var(--hm-color-surface)', border: '1px solid var(--hm-color-border)', borderRadius: 8 }} />
                    <Panel position="top-left" style={{ background: 'var(--hm-color-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--hm-color-border)', color: 'white' }}>
                        <Flex vertical gap={8}>
                            <Title level={5} style={{ margin: 0 }}><SettingOutlined /> Builder</Title>
                            <Flex gap={8} align="center">
                                <Select
                                    value={pipelineType}
                                    onChange={setPipelineType}
                                    size="small"
                                    options={[
                                        { value: 'ingestion', label: 'Ingestion Pipeline' },
                                        { value: 'retrieval', label: 'Retrieval Pipeline' }
                                    ]}
                                    style={{ width: 140 }}
                                />
                                <Tag color="processing">Active</Tag>
                            </Flex>
                        </Flex>
                    </Panel>
                    <Panel position="top-right">
                        <Flex gap={8}>
                            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                                Save
                            </Button>
                            <Button type="default" icon={<PlayCircleOutlined />}>
                                Test
                            </Button>
                        </Flex>
                    </Panel>
                </ReactFlow>

                {/* Node Config Drawer */}
                <Drawer
                    title={`Configure: ${(selectedNode?.data?.label as string) || 'Node'}`}
                    placement="right"
                    onClose={() => setConfigVisible(false)}
                    open={configVisible}
                    width={320}
                    footer={
                        <Flex justify="flex-end" gap={8} style={{ padding: '8px 0' }}>
                            <Button onClick={() => setConfigVisible(false)}>Cancel</Button>
                            <Button type="primary" onClick={handleSaveConfig}>Apply</Button>
                        </Flex>
                    }
                    styles={{ body: { padding: '16px' } }}
                >
                    <Form form={form} layout="vertical">
                        {(selectedNode?.data?.label as string)?.includes('Chunking') && (
                            <>
                                <Form.Item label="Chunk Size" name="chunkSize" initialValue={1000}>
                                    <InputNumber style={{ width: '100%' }} />
                                </Form.Item>
                                <Form.Item label="Chunk Overlap" name="chunkOverlap" initialValue={200}>
                                    <InputNumber style={{ width: '100%' }} />
                                </Form.Item>
                            </>
                        )}
                        {(selectedNode?.data?.label as string)?.includes('Desensitization') && (
                            <>
                                <Form.Item label="Policy Name" name="policyName" initialValue="Default_PII">
                                    <Select options={[{ value: 'Default_PII', label: 'Default PII' }, { value: 'Strict_BSI', label: 'Strict BSI' }]} />
                                </Form.Item>
                                <Form.Item label="Action" name="action" initialValue="mask">
                                    <Select options={[{ value: 'mask', label: 'Masking (*)' }, { value: 'remove', label: 'Remove' }, { value: 'warn', label: 'Warn Only' }]} />
                                </Form.Item>
                            </>
                        )}
                        {(selectedNode?.data?.label as string)?.includes('Parser') && (
                            <>
                                <Form.Item label="OCR Strategy" name="ocrStrategy" initialValue="auto">
                                    <Select options={[{ value: 'auto', label: 'Auto (Fast)' }, { value: 'force', label: 'Force OCR (Accurate)' }]} />
                                </Form.Item>
                                <Form.Item label="Extract Images" name="extractImages" initialValue={true} valuePropName="checked">
                                    <Switch />
                                </Form.Item>
                            </>
                        )}
                        {(selectedNode?.data?.label as string)?.includes('Rewrite') && (
                            <>
                                <Form.Item label="Enable HyDE" name="enableHyDE" initialValue={true} valuePropName="checked">
                                    <Switch />
                                </Form.Item>
                                <Form.Item label="Rewrite Model" name="rewriteModel" initialValue="gpt-4o-mini">
                                    <Select options={[{ value: 'gpt-4o-mini', label: 'gpt-4o-mini' }, { value: 'claude-3-haiku', label: 'claude-3-haiku' }]} />
                                </Form.Item>
                            </>
                        )}
                        {(selectedNode?.data?.label as string)?.includes('Search') && (
                            <>
                                <Form.Item label="Top K" name="topK" initialValue={5}>
                                    <InputNumber style={{ width: '100%' }} />
                                </Form.Item>
                                <Form.Item label="Similarity Threshold" name="similarityThreshold" initialValue={0.6}>
                                    <InputNumber step={0.1} min={0} max={1} style={{ width: '100%' }} />
                                </Form.Item>
                            </>
                        )}
                        {(selectedNode?.data?.label as string)?.includes('Reranker') && (
                            <>
                                <Form.Item label="Rerank Model" name="rerankModel" initialValue="bge-reranker-v2-m3">
                                    <Select options={[{ value: 'bge-reranker-v2-m3', label: 'BGE Reranker V2 M3' }, { value: 'cohere-rerank-v3', label: 'Cohere Rerank V3' }]} />
                                </Form.Item>
                            </>
                        )}
                        <Form.Item label="Description (Optional)" name="description">
                            <Input.TextArea rows={2} />
                        </Form.Item>
                    </Form>
                </Drawer>
            </Content>
        </Layout>
    );
};

export const PipelineBuilderPage: React.FC = () => {
    return (
        <Card bodyStyle={{ padding: 0 }} bordered={false} style={{ background: 'transparent' }}>
            <ReactFlowProvider>
                <DnDFlow />
            </ReactFlowProvider>
            <style>{`
                /* Make the React Flow handles much larger and visible so users know they can connect them */
                .react-flow__handle {
                    width: 12px;
                    height: 12px;
                    background: #1890ff;
                    border: 2px solid #fff;
                    cursor: crosshair;
                }
                .react-flow__handle:hover {
                    background: #ff4d4f;
                    transform: scale(1.3);
                    transition: all 0.2s;
                }
            `}</style>
        </Card>
    );
};
