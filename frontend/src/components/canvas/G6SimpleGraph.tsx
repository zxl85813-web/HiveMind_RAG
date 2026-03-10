import React, { useEffect, useRef, useState } from 'react';
import { Button, Flex, Space, Tag, Typography } from 'antd';
import { AimOutlined, PlusOutlined, MinusOutlined, RadarChartOutlined } from '@ant-design/icons';
import { Graph } from '@antv/g6';

interface G6SimpleGraphProps {
    height?: number;
}

const { Text } = Typography;

const baseData = {
    nodes: [
        { id: 'supervisor', data: { label: 'Supervisor', status: 'running' } },
        { id: 'rag', data: { label: 'RAG Agent', status: 'running' } },
        { id: 'web', data: { label: 'Web Agent', status: 'idle' } },
        { id: 'reflect', data: { label: 'Reflect Agent', status: 'idle' } },
        { id: 'memory', data: { label: 'Shared Memory', status: 'stable' } },
    ],
    edges: [
        { source: 'supervisor', target: 'rag', data: { label: 'dispatch' } },
        { source: 'supervisor', target: 'web', data: { label: 'dispatch' } },
        { source: 'supervisor', target: 'reflect', data: { label: 'review' } },
        { source: 'rag', target: 'memory', data: { label: 'write' } },
        { source: 'web', target: 'memory', data: { label: 'write' } },
        { source: 'reflect', target: 'memory', data: { label: 'write' } },
    ],
};

export const G6SimpleGraph: React.FC<G6SimpleGraphProps> = ({ height = 420 }) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const graphRef = useRef<Graph | null>(null);
    const [focusNode, setFocusNode] = useState('supervisor');

    const zoomIn = () => {
        const graph = graphRef.current as any;
        graph?.zoomBy?.(1.1);
    };

    const zoomOut = () => {
        const graph = graphRef.current as any;
        graph?.zoomBy?.(0.9);
    };

    const fitView = () => {
        const graph = graphRef.current as any;
        graph?.fitView?.();
    };

    const focusMemory = () => {
        const graph = graphRef.current as any;
        graph?.focusElement?.('memory', true);
        setFocusNode('memory');
    };

    useEffect(() => {
        if (!containerRef.current) {
            return;
        }

        const graph = new Graph({
            container: containerRef.current,
            width: containerRef.current.clientWidth,
            height,
            autoFit: 'view',
            data: baseData,
            node: {
                type: 'rect',
                style: {
                    size: [150, 44],
                    radius: 8,
                    lineWidth: 1,
                    stroke: 'rgba(255,255,255,0.2)',
                    labelText: (d: { data?: { label?: string } }) => d?.data?.label || '',
                    labelFill: '#F8FAFC',
                    labelFontSize: 12,
                    fill: (d: { data?: { status?: string } }) => {
                        if (d?.data?.status === 'running') return '#118AB2';
                        if (d?.data?.status === 'stable') return '#06D6A0';
                        return '#1F2937';
                    },
                },
            },
            edge: {
                type: 'line',
                style: {
                    stroke: 'rgba(255,255,255,0.25)',
                    lineWidth: 2,
                    endArrow: true,
                    labelText: (d: { data?: { label?: string } }) => d?.data?.label || '',
                    labelFill: '#94A3B8',
                    labelFontSize: 10,
                },
            },
            layout: {
                type: 'dagre',
                rankdir: 'LR',
                nodesep: 36,
                ranksep: 56,
            },
            behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
        });
        graphRef.current = graph;

        graph.render();

        (graph as any).on('node:click', (evt: { target?: { id?: string } }) => {
            if (evt?.target?.id) {
                setFocusNode(evt.target.id);
            }
        });

        const onResize = () => {
            if (containerRef.current) {
                graph.setSize(containerRef.current.clientWidth, height);
            }
        };

        window.addEventListener('resize', onResize);

        return () => {
            window.removeEventListener('resize', onResize);
            graph.destroy();
            graphRef.current = null;
        };
    }, [height]);

    return (
        <Flex vertical gap={12}>
            <Flex justify="space-between" align="center" wrap="wrap" gap={10}>
                <Space size={8}>
                    <Button icon={<MinusOutlined />} onClick={zoomOut} size="small" />
                    <Button icon={<PlusOutlined />} onClick={zoomIn} size="small" />
                    <Button icon={<AimOutlined />} onClick={fitView} size="small">归中</Button>
                    <Button icon={<RadarChartOutlined />} onClick={focusMemory} size="small">聚焦 Memory</Button>
                </Space>
                <Space size={8}>
                    <Tag color="blue">Running</Tag>
                    <Tag color="default">Idle</Tag>
                    <Tag color="success">Stable</Tag>
                    <Tag color="processing">Focus: {focusNode}</Tag>
                </Space>
            </Flex>
            <Text type="secondary">提示: 可拖拽画布、缩放、点击节点查看当前聚焦目标。</Text>
            <div ref={containerRef} style={{ width: '100%', height, borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)' }} />
        </Flex>
    );
};
