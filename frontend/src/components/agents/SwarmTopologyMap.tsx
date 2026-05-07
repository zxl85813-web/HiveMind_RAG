/**
 * SwarmTopologyMap — Agent-Skill-Tool 能力拓扑可视化。
 *
 * 三类节点:
 *   🤖 agent  — 注册的 Agent (绿色, 大圆)
 *   ⚡ skill   — 绑定的 Skill (紫色, 菱形)
 *   🔌 tool    — 可用的 MCP/原生 Tool (青色, 小圆)
 *
 * 连线:
 *   agent → skill  (rel: "uses",    紫色虚线粒子)
 *   agent → tool   (rel: "has_tool", 青色实线粒子)
 */

import React, { useRef, useEffect, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import { Space, Badge, Typography } from 'antd';
import { useWindowSize } from '../../hooks/useWindowSize';
import type { TopologyData, TopologyNode, TopologyLink } from '../../services/agentApi';

const { Text } = Typography;

interface SwarmTopologyMapProps {
    data: TopologyData;
    height?: number;
}

// 节点类型颜色 / 大小
const NODE_CONFIG = {
    agent: { color: '#06D6A0', size: 14, border: '#06D6A0' },
    skill: { color: '#a855f7', size: 10, border: '#c084fc' },
    tool:  { color: '#06b6d4', size:  7, border: '#67e8f9' },
} as const;

const LINK_COLOR = {
    uses:     'rgba(168, 85, 247, 0.55)',
    has_tool: 'rgba(6, 182, 212, 0.45)',
} as const;

const PARTICLE_COLOR = {
    uses:     '#c084fc',
    has_tool: '#67e8f9',
} as const;

export const SwarmTopologyMap: React.FC<SwarmTopologyMapProps> = ({ data, height = 460 }) => {
    const graphRef = useRef<ForceGraphMethods | undefined>(undefined);
    const { width: windowWidth } = useWindowSize();
    const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });

    // Deep clone to avoid mutations inside force-graph
    useEffect(() => {
        setGraphData({
            nodes: data.nodes.map(n => ({ ...n })),
            links: data.links.map(l => ({ ...l })),
        });
    }, [data]);

    // Tune physics
    useEffect(() => {
        if (graphRef.current) {
            const g = graphRef.current as any;
            g.d3Force('charge')?.strength(-350);
            g.d3Force('link')?.distance((link: any) => {
                const src = typeof link.source === 'object' ? (link.source as TopologyNode).type : 'agent';
                return src === 'agent' ? 140 : 90;
            });
        }
    }, [graphData]);

    // Auto center & zoom to fit on data or window size change
    useEffect(() => {
        const timer = setTimeout(() => {
            if (graphRef.current && graphData.nodes.length > 0) {
                graphRef.current.zoomToFit(400, 30);
            }
        }, 500);
        return () => clearTimeout(timer);
    }, [graphData, windowWidth]);

    const containerWidth = useMemo(
        () => (windowWidth ? windowWidth - 400 : 800),
        [windowWidth]
    );

    const drawNode = (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const type = (node.type as keyof typeof NODE_CONFIG) || 'tool';
        const cfg = NODE_CONFIG[type];
        const r = cfg.size / globalScale;
        const fontSize = Math.max(9, 11 / globalScale);

        // Glow for agent nodes
        if (type === 'agent') {
            ctx.shadowBlur = 20 / globalScale;
            ctx.shadowColor = cfg.color;
        }

        // Draw shape: diamond for skills, circle for agents/tools
        ctx.beginPath();
        if (type === 'skill') {
            const d = r * 1.4;
            ctx.moveTo(node.x, node.y - d);
            ctx.lineTo(node.x + d, node.y);
            ctx.lineTo(node.x, node.y + d);
            ctx.lineTo(node.x - d, node.y);
            ctx.closePath();
        } else {
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
        }
        ctx.fillStyle = `${cfg.color}22`;
        ctx.fill();
        ctx.strokeStyle = cfg.border;
        ctx.lineWidth = (type === 'agent' ? 2 : 1.2) / globalScale;
        ctx.stroke();

        ctx.shadowBlur = 0;

        // Draw label
        ctx.font = `${type === 'agent' ? 'bold ' : ''}${fontSize}px "Inter", -apple-system, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        // Label background
        const labelText = node.label as string;
        const textWidth = ctx.measureText(labelText).width;
        const pad = 3 / globalScale;
        const labelY = node.y + r + 4 / globalScale;
        ctx.fillStyle = 'rgba(10,14,26,0.75)';
        ctx.fillRect(node.x - textWidth / 2 - pad, labelY - pad / 2, textWidth + pad * 2, fontSize + pad);

        ctx.fillStyle = cfg.color;
        ctx.fillText(labelText, node.x, labelY);

        // Hit area cache
        node.__r = r;
    };

    return (
        <div style={{ position: 'relative', width: '100%', overflow: 'hidden', borderRadius: 8 }}>
            {/* Legend */}
            <div style={{
                position: 'absolute', top: 12, left: 12, zIndex: 10,
                background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(8px)',
                padding: '10px 14px', borderRadius: 8,
                border: '1px solid rgba(255,255,255,0.08)',
            }}>
                <Text strong style={{ color: '#fff', fontSize: 11, display: 'block', marginBottom: 6 }}>
                    节点类型
                </Text>
                <Space direction="vertical" size={4}>
                    <Space size={6}><Badge color="#06D6A0" /><Text style={{ color: '#ccc', fontSize: 11 }}>Agent（编排器）</Text></Space>
                    <Space size={6}><Badge color="#a855f7" /><Text style={{ color: '#ccc', fontSize: 11 }}>Skill（能力包）</Text></Space>
                    <Space size={6}><Badge color="#06b6d4" /><Text style={{ color: '#ccc', fontSize: 11 }}>MCP Tool（工具）</Text></Space>
                </Space>
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <Space direction="vertical" size={3}>
                        <Space size={6}>
                            <span style={{ display: 'inline-block', width: 20, height: 1, background: '#c084fc', verticalAlign: 'middle' }} />
                            <Text style={{ color: '#ccc', fontSize: 10 }}>uses (调用 Skill)</Text>
                        </Space>
                        <Space size={6}>
                            <span style={{ display: 'inline-block', width: 20, height: 1, background: '#67e8f9', verticalAlign: 'middle' }} />
                            <Text style={{ color: '#ccc', fontSize: 10 }}>has_tool (持有工具)</Text>
                        </Space>
                    </Space>
                </div>
            </div>

            <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                width={containerWidth}
                height={height}
                backgroundColor="transparent"
                nodeRelSize={6}
                nodeCanvasObject={drawNode}
                nodePointerAreaPaint={(node: any, color, ctx) => {
                    const r = (node.__r || 10) * 2;
                    ctx.fillStyle = color;
                    ctx.fillRect(node.x - r, node.y - r, r * 2, r * 2);
                }}
                linkColor={(link: any) => {
                    const rel = (link.rel as keyof typeof LINK_COLOR) || 'has_tool';
                    return LINK_COLOR[rel];
                }}
                linkWidth={1.2}
                linkDirectionalParticles={2}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleSpeed={0.007}
                linkDirectionalParticleColor={(link: any) => {
                    const rel = (link.rel as keyof typeof PARTICLE_COLOR) || 'has_tool';
                    return PARTICLE_COLOR[rel];
                }}
                linkDirectionalArrowLength={5}
                linkDirectionalArrowRelPos={1}
                linkDirectionalArrowColor={(link: any) => {
                    const rel = (link.rel as keyof typeof LINK_COLOR) || 'has_tool';
                    return LINK_COLOR[rel];
                }}
                minZoom={0.3}
                maxZoom={6}
                cooldownTicks={120}
                onEngineStop={() => {
                    graphRef.current?.zoomToFit(400, 30);
                }}
                onNodeClick={(node: any) => {
                    graphRef.current?.centerAt(node.x, node.y, 400);
                    graphRef.current?.zoom(2.5, 400);
                }}
            />
        </div>
    );
};
