import React, { useCallback, useRef, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import * as d3 from 'd3-force';
import { theme } from 'antd';

interface GraphVisualizerProps {
    data: {
        nodes: any[];
        links: any[];
    };
    width?: number;
    height?: number;
    onNodeClick?: (node: any) => void;
}

export const GraphVisualizer: React.FC<GraphVisualizerProps> = ({ data, width, height, onNodeClick }) => {
    const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const [ready, setReady] = useState(false);
    const { token } = theme.useToken();

    // Measure once the container is mounted
    useEffect(() => {
        const timer = setTimeout(() => {
            if (containerRef.current) {
                const w = width || containerRef.current.clientWidth || 600;
                const h = height || containerRef.current.clientHeight || 500;
                setDimensions({ width: Math.max(w, 200), height: Math.max(h, 200) });
                setReady(true);
            }
        }, 100); // Small delay to let Drawer animate open
        return () => clearTimeout(timer);
    }, [width, height]);

    // Re-measure on window resize
    useEffect(() => {
        const handleResize = () => {
            if (containerRef.current) {
                const w = width || containerRef.current.clientWidth || 600;
                const h = height || containerRef.current.clientHeight || 500;
                setDimensions({ width: Math.max(w, 200), height: Math.max(h, 200) });
            }
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [width, height]);

    useEffect(() => {
        if (!ready) return;
        // Tuning force parameters for better visual layout
        const fg = fgRef.current;
        if (fg) {
            fg.d3Force('charge', d3.forceManyBody().strength(-200));
            fg.d3Force('link', d3.forceLink().distance(80));
            fg.d3Force('center', d3.forceCenter(0, 0));
        }
    }, [data, ready]);

    // Draw customized nodes
    const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = node.name || node.id || 'Unknown';
        const fontSize = 12 / globalScale;

        ctx.font = `${fontSize}px Sora, sans-serif`;
        const radius = node.val || 5;

        // Node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = node.color || token.colorPrimary;
        ctx.fill();

        // Node Glow/Stroke
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.stroke();

        // Label
        if (globalScale > 0.8) {
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = token.colorText;
            ctx.fillText(label, node.x, node.y + radius + fontSize);
        }
    }, [token.colorPrimary, token.colorText]);

    // Draw customized links (arrows if directional)
    const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const start = link.source;
        const end = link.target;

        // Skip if coordinates are broken
        if (typeof start.x !== 'number' || typeof end.x !== 'number') return;

        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)'; // Subtle edge
        ctx.lineWidth = Math.max(0.5, 1 / globalScale);
        ctx.stroke();

        // Edge Label (Relationship)
        if (link.type && globalScale > 1.2) {
            const midX = start.x + (end.x - start.x) / 2;
            const midY = start.y + (end.y - start.y) / 2;
            const linkFontSize = 6 / globalScale;
            ctx.font = `${linkFontSize}px Sora, sans-serif`;
            ctx.fillStyle = token.colorTextSecondary;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(link.type, midX, midY);
        }
    }, [token.colorTextSecondary]);

    return (
        <div ref={containerRef} style={{ width: '100%', height: '100%', minHeight: 400, position: 'relative', overflow: 'hidden', background: 'transparent' }}>
            {ready && dimensions.width > 0 && (
                <ForceGraph2D
                    ref={fgRef}
                    width={dimensions.width}
                    height={dimensions.height}
                    graphData={data}
                    nodeCanvasObject={paintNode}
                    linkCanvasObjectMode={() => 'replace'}
                    linkCanvasObject={paintLink}
                    onNodeClick={(node) => {
                        // Center on click
                        fgRef.current?.centerAt(node.x, node.y, 1000);
                        fgRef.current?.zoom(2, 1000);
                        if (onNodeClick) onNodeClick(node);
                    }}
                    nodeRelSize={6}
                    linkColor={() => 'rgba(255,255,255,0.1)'}
                    backgroundColor="transparent"
                    cooldownTicks={100}
                    onEngineStop={() => fgRef.current?.zoomToFit(400, 20)}
                />
            )}
            {/* Overlay hint */}
            <div style={{ position: 'absolute', bottom: 12, left: 12, fontSize: 12, color: 'rgba(255,255,255,0.4)', pointerEvents: 'none' }}>
                支持拖拽、滚轮缩放与节点点击
            </div>
        </div>
    );
};
