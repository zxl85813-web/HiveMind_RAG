import React, { useEffect, useRef, useState } from 'react';
import { Button, Flex, Space, Tag, Typography, theme } from 'antd';
import {
    AimOutlined,
    MinusOutlined,
    PlusOutlined,
    NodeIndexOutlined,
    ReloadOutlined,
    FileTextOutlined,
    PictureOutlined,
    VideoCameraOutlined,
    AppstoreOutlined,
    UploadOutlined,
    DeleteOutlined,
    LinkOutlined,
    ScissorOutlined,
} from '@ant-design/icons';
import { Graph } from '@antv/x6';

interface X6SimpleCanvasProps {
    height?: number;
}

const { Text } = Typography;

export const X6SimpleCanvas: React.FC<X6SimpleCanvasProps> = ({ height = 420 }) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const graphRef = useRef<Graph | null>(null);
    const stepCounterRef = useRef(1);
    const selectedNodeIdRef = useRef<string | null>(null);
    const selectedEdgeIdRef = useRef<string | null>(null);
    const [selectedNode, setSelectedNode] = useState('未选中节点');
    const [selectedEdge, setSelectedEdge] = useState('未选中连线');
    const [nodeCount, setNodeCount] = useState(0);
    const [menuOpen, setMenuOpen] = useState(false);
    const [menuPosition, setMenuPosition] = useState({ x: 120, y: 120 });
    const [connectMode, setConnectMode] = useState(false);
    const [connectSourceLabel, setConnectSourceLabel] = useState('');
    const connectModeRef = useRef(false);
    const connectSourceLabelRef = useRef('');
    const pendingNodePointRef = useRef<{ x: number; y: number } | null>(null);
    const { token } = theme.useToken();

    useEffect(() => {
        connectModeRef.current = connectMode;
    }, [connectMode]);

    useEffect(() => {
        connectSourceLabelRef.current = connectSourceLabel;
    }, [connectSourceLabel]);

    const createStyledEdge = (sourceCellId: string, targetCellId: string, labelText: string) => {
        const graph = graphRef.current;
        if (!graph) return;
        graph.addEdge({
            source: { cell: sourceCellId, port: 'out' },
            target: { cell: targetCellId, port: 'in' },
            attrs: {
                line: {
                    stroke: token.colorInfo,
                    strokeWidth: 2,
                    strokeDasharray: '8 6',
                    strokeLinecap: 'round',
                    style: {
                        animation: 'hm-edge-flow 7s linear infinite',
                        filter: 'drop-shadow(0 0 6px rgba(17,138,178,0.35))',
                    },
                    targetMarker: {
                        name: 'block',
                        width: 12,
                        height: 8,
                    },
                },
            },
            labels: [{
                attrs: {
                    label: {
                        text: labelText,
                        fill: token.colorBgLayout,
                        fontSize: 11,
                        fontWeight: 600,
                        textDecoration: 'none',
                    },
                    body: {
                        fill: 'rgba(255,255,255,0.96)',
                        stroke: 'transparent',
                        strokeWidth: 0,
                        rx: 6,
                        ry: 6,
                    },
                },
            }],
        });
    };

    const createWorkflowNode = (x: number, y: number, labelOverride?: string, fillOverride?: string) => {
        const graph = graphRef.current;
        if (!graph) return;

        const nextIndex = stepCounterRef.current;
        const node = graph.addNode({
            x,
            y,
            width: 190,
            height: 52,
            label: labelOverride || `Verifier ${nextIndex}`,
            attrs: {
                body: {
                    fill: fillOverride || token.colorBgElevated,
                    stroke: 'rgba(255,255,255,0.18)',
                    rx: 10,
                    ry: 10,
                },
                label: {
                    fill: token.colorText,
                    fontSize: 13,
                },
            },
            ports: {
                groups: {
                    in: {
                        position: 'left',
                        attrs: {
                            circle: {
                                r: 5,
                                magnet: true,
                                stroke: token.colorPrimary,
                                strokeWidth: 2,
                                fill: token.colorBgLayout,
                            },
                        },
                    },
                    out: {
                        position: 'right',
                        attrs: {
                            circle: {
                                r: 5,
                                magnet: true,
                                stroke: token.colorPrimary,
                                strokeWidth: 2,
                                fill: token.colorBgLayout,
                            },
                        },
                    },
                },
                items: [{ group: 'in' }, { group: 'out' }],
            },
        });

        const sourceNodeId = selectedNodeIdRef.current;
        if (sourceNodeId) {
            createStyledEdge(sourceNodeId, node.id, 'validate');
        }

        selectedNodeIdRef.current = node.id;
        setSelectedNode(node.getProp('label') as string);
        stepCounterRef.current += 1;
        setNodeCount(graph.getNodes().length);
    };

    const addFollowupStep = () => {
        const graph = graphRef.current;
        if (!graph) return;

        const nodes = graph.getNodes();
        const lastNode = nodes[nodes.length - 1];
        const x = (lastNode?.position().x || 640) + 240;
        const y = lastNode?.position().y || 140;
        createWorkflowNode(x, y);
    };

    const addNodeAtViewportCenter = () => {
        const graph = graphRef.current;
        if (!graph || !containerRef.current) return;

        const rect = containerRef.current.getBoundingClientRect();
        const center = graph.clientToLocal(rect.left + rect.width / 2, rect.top + rect.height / 2);
        createWorkflowNode(center.x - 90, center.y - 26);
    };

    const removeSelection = () => {
        const graph = graphRef.current;
        if (!graph) return;

        if (selectedEdgeIdRef.current) {
            const edge = graph.getCellById(selectedEdgeIdRef.current);
            edge?.remove();
            selectedEdgeIdRef.current = null;
            setSelectedEdge('未选中连线');
            return;
        }

        if (selectedNodeIdRef.current) {
            const node = graph.getCellById(selectedNodeIdRef.current);
            node?.remove();
            selectedNodeIdRef.current = null;
            setSelectedNode('未选中节点');
            setNodeCount(graph.getNodes().length);
        }
    };

    const toggleConnectMode = () => {
        setConnectMode((prev) => {
            if (prev) {
                setConnectSourceLabel('');
            }
            return !prev;
        });
    };

    const createNodeFromMenu = (label: string, fill: string) => {
        const point = pendingNodePointRef.current;
        if (!point) return;
        createWorkflowNode(point.x - 90, point.y - 26, label, fill);
        setMenuOpen(false);
    };

    const resetViewport = () => {
        const graph = graphRef.current;
        if (!graph) return;
        graph.zoomTo(1);
        graph.centerContent();
    };

    const zoomIn = () => {
        graphRef.current?.zoom(0.1);
    };

    const zoomOut = () => {
        graphRef.current?.zoom(-0.1);
    };

    useEffect(() => {
        if (!containerRef.current) {
            return;
        }

        const graph = new Graph({
            container: containerRef.current,
            background: {
                color: token.colorBgLayout,
            },
            grid: {
                visible: true,
                type: 'dot',
                size: 14,
                args: {
                    color: 'rgba(255, 255, 255, 0.08)',
                },
            },
            panning: true,
            mousewheel: {
                enabled: true,
                modifiers: ['ctrl', 'meta'],
                minScale: 0.5,
                maxScale: 1.8,
            },
            connecting: {
                router: 'manhattan',
                connector: 'rounded',
                allowBlank: false,
                allowLoop: false,
            },
        });
        graphRef.current = graph;

        graph.on('node:click', ({ node }) => {
            const label = node.getProp('label');
            setSelectedNode(typeof label === 'string' ? label : node.id);
            selectedNodeIdRef.current = node.id;

            if (connectModeRef.current) {
                const selectedLabel = typeof label === 'string' ? label : node.id;
                if (!connectSourceLabelRef.current) {
                    setConnectSourceLabel(selectedLabel);
                } else {
                    const allNodes = graph.getNodes();
                    const sourceNode = allNodes.find((n) => {
                        const currentLabel = n.getProp('label');
                        return (typeof currentLabel === 'string' ? currentLabel : n.id) === connectSourceLabelRef.current;
                    });
                    if (sourceNode && sourceNode.id !== node.id) {
                        createStyledEdge(sourceNode.id, node.id, 'manual-link');
                    }
                    setConnectSourceLabel('');
                }
            }
        });

        graph.on('edge:click', ({ edge }) => {
            selectedEdgeIdRef.current = edge.id;
            setSelectedEdge(edge.id);
        });

        graph.on('blank:dblclick', (evt: any) => {
            const x = typeof evt?.x === 'number' ? evt.x : 120;
            const y = typeof evt?.y === 'number' ? evt.y : 120;
            pendingNodePointRef.current = { x, y };

            const clientX = evt?.e?.clientX;
            const clientY = evt?.e?.clientY;
            if (typeof clientX === 'number' && typeof clientY === 'number' && containerRef.current) {
                const rect = containerRef.current.getBoundingClientRect();
                setMenuPosition({
                    x: Math.max(12, clientX - rect.left),
                    y: Math.max(12, clientY - rect.top),
                });
            }
            setMenuOpen(true);
        });

        graph.on('blank:click', () => {
            setMenuOpen(false);
            selectedEdgeIdRef.current = null;
            setSelectedEdge('未选中连线');
        });

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Delete' || event.key === 'Backspace') {
                removeSelection();
            }
        };
        document.addEventListener('keydown', handleKeyDown);

        const source = graph.addNode({
            x: 80,
            y: 140,
            width: 180,
            height: 52,
            label: 'Input Query',
            attrs: {
                body: {
                    fill: token.colorInfo,
                    stroke: 'rgba(255,255,255,0.18)',
                    rx: 10,
                    ry: 10,
                },
                label: {
                    fill: token.colorText,
                    fontSize: 13,
                },
            },
            ports: {
                groups: {
                    out: {
                        position: 'right',
                        attrs: {
                            circle: {
                                r: 5,
                                magnet: true,
                                stroke: token.colorPrimary,
                                strokeWidth: 2,
                                fill: token.colorBgLayout,
                            },
                        },
                    },
                },
                items: [{ group: 'out' }],
            },
        });

        const retrieve = graph.addNode({
            x: 340,
            y: 140,
            width: 200,
            height: 52,
            label: 'Hybrid Retrieval',
            attrs: {
                body: {
                    fill: token.colorBgElevated,
                    stroke: 'rgba(255,255,255,0.18)',
                    rx: 10,
                    ry: 10,
                },
                label: {
                    fill: token.colorText,
                    fontSize: 13,
                },
            },
            ports: {
                groups: {
                    in: {
                        position: 'left',
                        attrs: {
                            circle: {
                                r: 5,
                                magnet: true,
                                stroke: token.colorPrimary,
                                strokeWidth: 2,
                                fill: token.colorBgLayout,
                            },
                        },
                    },
                    out: {
                        position: 'right',
                        attrs: {
                            circle: {
                                r: 5,
                                magnet: true,
                                stroke: token.colorPrimary,
                                strokeWidth: 2,
                                fill: token.colorBgLayout,
                            },
                        },
                    },
                },
                items: [{ group: 'in' }, { group: 'out' }],
            },
        });

        const answer = graph.addNode({
            x: 640,
            y: 140,
            width: 180,
            height: 52,
            label: 'Generate Answer',
            attrs: {
                body: {
                    fill: token.colorPrimary,
                    stroke: 'rgba(255,255,255,0.18)',
                    rx: 10,
                    ry: 10,
                },
                label: {
                    fill: token.colorBgLayout,
                    fontSize: 13,
                    fontWeight: 600,
                },
            },
            ports: {
                groups: {
                    in: {
                        position: 'left',
                        attrs: {
                            circle: {
                                r: 5,
                                magnet: true,
                                stroke: token.colorPrimary,
                                strokeWidth: 2,
                                fill: token.colorBgLayout,
                            },
                        },
                    },
                },
                items: [{ group: 'in' }],
            },
        });

        createStyledEdge(source.id, retrieve.id, 'rewrite');
        createStyledEdge(retrieve.id, answer.id, 'top-k context');

        setNodeCount(graph.getNodes().length);
        graph.centerContent();

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            graph.dispose();
            graphRef.current = null;
        };
    }, [token.colorBgElevated, token.colorBgLayout, token.colorInfo, token.colorPrimary, token.colorText]);

    return (
        <Flex vertical gap={12}>
            <Flex justify="space-between" align="center" wrap="wrap" gap={10}>
                <Space size={8}>
                    <Button icon={<MinusOutlined />} onClick={zoomOut} size="small" />
                    <Button icon={<PlusOutlined />} onClick={zoomIn} size="small" />
                    <Button icon={<AimOutlined />} onClick={resetViewport} size="small">归中</Button>
                    <Button icon={<NodeIndexOutlined />} onClick={addFollowupStep} size="small">新增步骤</Button>
                    <Button onClick={addNodeAtViewportCenter} size="small">中心新增节点</Button>
                    <Button icon={<LinkOutlined />} onClick={toggleConnectMode} size="small" type={connectMode ? 'primary' : 'default'}>
                        连线模式
                    </Button>
                    <Button icon={<DeleteOutlined />} onClick={removeSelection} size="small" danger>
                        删除
                    </Button>
                </Space>
                <Space size={8}>
                    <Tag color="processing">Nodes: {nodeCount}</Tag>
                    <Tag color="success">Selected: {selectedNode}</Tag>
                    <Tag color="warning">Edge: {selectedEdge}</Tag>
                    {connectMode && (
                        <Tag icon={<ScissorOutlined />} color="volcano">
                            {connectSourceLabel ? `起点: ${connectSourceLabel}` : '连线模式: 先点起点再点终点'}
                        </Tag>
                    )}
                    <Button icon={<ReloadOutlined />} onClick={resetViewport} size="small" type="text">Reset</Button>
                </Space>
            </Flex>
            <Text type="secondary">提示: 双击空白区域会弹出“添加节点”面板；选中节点后再添加会自动连线。</Text>
            <div style={{ position: 'relative' }}>
                <div ref={containerRef} style={{ width: '100%', height, borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', boxShadow: 'inset 0 0 30px rgba(17,138,178,0.12)' }} />
                <div
                    style={{
                        position: 'absolute',
                        inset: 0,
                        pointerEvents: 'none',
                        borderRadius: 12,
                        background: 'radial-gradient(900px 320px at 85% 120%, rgba(6,214,160,0.14), transparent 55%), radial-gradient(720px 260px at 10% -10%, rgba(17,138,178,0.16), transparent 60%)',
                        mixBlendMode: 'screen',
                        opacity: 0.65,
                    }}
                />
                {menuOpen && (
                    <div
                        style={{
                            position: 'absolute',
                            left: menuPosition.x,
                            top: menuPosition.y,
                            width: 220,
                            background: 'linear-gradient(160deg, rgba(17,24,39,0.96), rgba(10,14,26,0.93))',
                            border: '1px solid rgba(148,163,184,0.2)',
                            borderRadius: 12,
                            backdropFilter: 'blur(12px)',
                            padding: 8,
                            zIndex: 20,
                            boxShadow: '0 18px 42px rgba(0,0,0,0.48), 0 0 24px rgba(17,138,178,0.2)',
                        }}
                    >
                        <Text style={{ color: token.colorTextSecondary, fontSize: 12, marginBottom: 6, display: 'block' }}>添加节点</Text>
                        <Button type="text" icon={<FileTextOutlined />} style={{ width: '100%', textAlign: 'left', justifyContent: 'flex-start', color: token.colorText }} onClick={() => createNodeFromMenu('文本', token.colorBgElevated)}>
                            文本
                        </Button>
                        <Button type="text" icon={<PictureOutlined />} style={{ width: '100%', textAlign: 'left', justifyContent: 'flex-start', color: token.colorText }} onClick={() => createNodeFromMenu('图片', token.colorInfo)}>
                            图片
                        </Button>
                        <Button type="text" icon={<VideoCameraOutlined />} style={{ width: '100%', textAlign: 'left', justifyContent: 'flex-start', color: token.colorText }} onClick={() => createNodeFromMenu('视频', token.colorBgElevated)}>
                            视频
                        </Button>
                        <Button type="text" icon={<AppstoreOutlined />} style={{ width: '100%', textAlign: 'left', justifyContent: 'flex-start', color: token.colorText }} onClick={() => createNodeFromMenu('分镜格子', token.colorPrimary)}>
                            分镜格子
                        </Button>
                        <Button type="text" icon={<UploadOutlined />} style={{ width: '100%', textAlign: 'left', justifyContent: 'flex-start', color: token.colorText }} onClick={() => createNodeFromMenu('上传', token.colorInfo)}>
                            上传
                        </Button>
                    </div>
                )}
                <style>
                    {`@keyframes hm-edge-flow { from { stroke-dashoffset: 0; } to { stroke-dashoffset: -84; } }`}
                </style>
            </div>
        </Flex>
    );
};
