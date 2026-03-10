import React, { useRef, useEffect, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import { useWindowSize } from '../../hooks/useWindowSize';
import { Space, Badge, Typography, theme } from 'antd';

const { Text } = Typography;

export interface DAGNode {
    id: string;
    label: string;
    agent: string;
    status: 'pending' | 'running' | 'completed' | 'error' | 'warning';
    duration?: string;
    x?: number;
    y?: number;
}

export interface DAGLink {
    source: string | DAGNode;
    target: string | DAGNode;
    label?: string;
}

export interface DAGData {
    nodes: DAGNode[];
    links: DAGLink[];
}

interface AgentDAGVisualizerProps {
    data: DAGData;
    height?: number;
    width?: number;
}

export const AgentDAGVisualizer: React.FC<AgentDAGVisualizerProps> = ({ data, height, width }) => {
    const graphRef = useRef<ForceGraphMethods | undefined>(undefined);
    const { width: windowWidth } = useWindowSize();
    const [graphData, setGraphData] = useState<DAGData>({ nodes: [], links: [] });
    const { token } = theme.useToken();

    const withAlpha = (color: string, alpha: number): string => {
        const normalized = color.trim();
        const hexMatch = normalized.match(/^#([0-9a-f]{6}|[0-9a-f]{3})$/i);
        if (hexMatch) {
            const hex = hexMatch[1];
            const fullHex = hex.length === 3 ? hex.split('').map((ch) => ch + ch).join('') : hex;
            const r = parseInt(fullHex.slice(0, 2), 16);
            const g = parseInt(fullHex.slice(2, 4), 16);
            const b = parseInt(fullHex.slice(4, 6), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        return normalized;
    };

    const statusColors = useMemo(() => ({
        completed: token.colorSuccess,
        running: token.colorInfo,
        error: token.colorError,
        warning: token.colorWarning,
        pending: token.colorTextSecondary
    }), [token.colorError, token.colorInfo, token.colorSuccess, token.colorTextSecondary, token.colorWarning]);

    useEffect(() => {
        // Deep clone data to avoid mutation issues in force-graph
        setGraphData({
            nodes: data.nodes.map(n => ({ ...n })),
            links: data.links.map(l => ({ ...l }))
        });
    }, [data]);

    useEffect(() => {
        if (graphRef.current) {
            // Adjust physics forces for DAG
            const g = graphRef.current as any;
            g.d3Force('charge')?.strength(-500);
            g.d3Force('link')?.distance(100);
        }
    }, [graphData]);

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
            {/* Legend Overlay */}
            <div style={{
                position: 'absolute',
                top: 16,
                left: 16,
                zIndex: 10,
                background: 'rgba(0,0,0,0.6)',
                backdropFilter: 'blur(8px)',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.1)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}>
                <Space direction="vertical" size={4}>
                    <Text strong style={{ color: token.colorText, fontSize: '11px', marginBottom: 4, display: 'block' }}>状态说明 / Status Legend</Text>
                    {Object.entries(statusColors).map(([status, color]) => (
                        <Space key={status} size={8}>
                            <Badge color={color} size="small" />
                            <Text style={{ color: token.colorTextSecondary, fontSize: '10px', textTransform: 'capitalize' }}>{status === 'running' ? '进行中' : status === 'completed' ? '已完成' : status === 'pending' ? '等待中' : status}</Text>
                        </Space>
                    ))}
                </Space>
                <div style={{ marginTop: 12, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                    <Text type="secondary" style={{ fontSize: '10px' }}>动画粒子代表实时数据流转</Text>
                </div>
            </div>

            <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                width={width || (windowWidth ? windowWidth * 0.6 : 800)}
                height={height || 400}
                dagMode="lr"
                dagLevelDistance={120}
                backgroundColor="transparent"
                nodeRelSize={8}
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                    const label = node.label;
                    const status = node.status as keyof typeof statusColors;
                    const color = statusColors[status] || statusColors.pending;

                    const fontSize = 11 / globalScale;
                    ctx.font = `${fontSize}px "Sora", sans-serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth + fontSize * 2, fontSize * 2.2];

                    // Draw Glow Effect for active/completed nodes
                    if (status === 'running' || status === 'completed') {
                        ctx.shadowBlur = 15 / globalScale;
                        ctx.shadowColor = color;
                    }

                    // Draw Node Background (Glassmorphism)
                    ctx.fillStyle = withAlpha(token.colorBgLayout, 0.95);
                    ctx.beginPath();
                    if (ctx.roundRect) {
                        ctx.roundRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1], 4 / globalScale);
                    } else {
                        ctx.rect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
                    }
                    ctx.fill();

                    ctx.shadowBlur = 0; // Reset shadow

                    // Draw Border
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 1.5 / globalScale;
                    ctx.stroke();

                    // Draw Agent Label (Small text above)
                    ctx.font = `${8 / globalScale}px "Sora"`;
                    ctx.fillStyle = withAlpha(token.colorText, 0.5);
                    ctx.textAlign = 'center';
                    ctx.fillText(node.agent.toUpperCase(), node.x, node.y - bckgDimensions[1] / 2 - 4 / globalScale);

                    // Draw Main Label
                    ctx.font = `bold ${fontSize}px "Sora"`;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = token.colorText;
                    ctx.fillText(label, node.x, node.y);

                    node.__bckgDimensions = bckgDimensions;
                }}
                nodePointerAreaPaint={(node: any, color, ctx) => {
                    ctx.fillStyle = color;
                    const bckgDimensions = node.__bckgDimensions;
                    if (bckgDimensions) {
                        ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
                    }
                }}
                // Link styling
                linkDirectionalParticles={2}
                linkDirectionalParticleSpeed={(d: any) => {
                    const target = d.target as DAGNode;
                    return target.status === 'running' ? 0.015 : 0.005;
                }}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleColor={() => token.colorPrimary}
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                linkColor={(link: any) => {
                    const target = link.target as DAGNode;
                    return target.status === 'completed' ? withAlpha(token.colorPrimary, 0.4) : withAlpha(token.colorText, 0.1);
                }}
                linkWidth={1.5}
                minZoom={0.2}
                maxZoom={5}
                cooldownTicks={100}
                onNodeClick={(node: any) => {
                    graphRef.current?.centerAt(node.x, node.y, 400);
                    graphRef.current?.zoom(2.5, 400);
                }}
            />
        </div>
    );
};
