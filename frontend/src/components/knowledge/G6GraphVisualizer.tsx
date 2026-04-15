import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Graph, Line, register, ExtensionCategory } from '@antv/g6';
import { theme, Checkbox, Space, Typography } from 'antd';

const { Text } = Typography;

/**
 * 自定义流动边 (Streaming Edge)
 * 基于 G6 v5.0 的动画系统实现“蚂蚁线”流动效果
 */
class FlowingEdge extends Line {
  onCreate() {
    super.onCreate();
    this.animate(
      [
        { lineDashOffset: 20 },
        { lineDashOffset: 0 },
      ],
      {
        duration: 2000,
        iterations: Infinity,
        easing: 'linear',
      }
    );
  }
}

// 注册自定义边
register(ExtensionCategory.EDGE, 'flowing-edge', FlowingEdge);

interface GraphData {
  nodes: { id: string; name?: string; color?: string; val?: number; [key: string]: any }[];
  links: { source: string; target: string; type?: string; [key: string]: any }[];
}

interface Props {
  data: GraphData;
  width?: number;
  height?: number;
  onNodeClick?: (node: any) => void;
}

export const G6GraphVisualizer: React.FC<Props> = ({ data, width, height, onNodeClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const { token } = theme.useToken();
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);

  // 0. 提取可用类型 (Labels)
  const availableTypes = useMemo(() => {
    if (!data?.nodes) return [];
    const types = new Set<string>();
    data.nodes.forEach(n => {
        const label = (Array.isArray(n.labels) ? n.labels[0] : n.type) || 'Unknown';
        types.add(label);
    });
    return Array.from(types);
  }, [data]);

  // 初始化全选
  useEffect(() => {
    if (availableTypes.length > 0 && selectedTypes.length === 0) {
        setSelectedTypes(availableTypes);
    }
  }, [availableTypes]);

  // 计算过滤后的数据
  const filteredData = useMemo(() => {
    if (!data || selectedTypes.length === 0) return data;
    const nodes = data.nodes.filter(n => {
        const label = (Array.isArray(n.labels) ? n.labels[0] : n.type) || 'Unknown';
        return selectedTypes.includes(label);
    });
    const nodeIds = new Set(nodes.map(n => n.id));
    const links = data.links.filter(l => 
        nodeIds.has(typeof l.source === 'object' ? (l.source as any).id : l.source) && 
        nodeIds.has(typeof l.target === 'object' ? (l.target as any).id : l.target)
    );
    return { nodes, links };
  }, [data, selectedTypes]);

  useEffect(() => {
    if (!containerRef.current || !filteredData) return;

    // 1. 数据转换
    const g6Data = {
      nodes: filteredData.nodes.map(n => ({
        id: n.id,
        data: {
          label: n.name || n.id,
          color: n.color || token.colorPrimary,
          size: (n.val || 5) * 4,
        },
        style: {
          fill: n.color || token.colorPrimary,
          stroke: 'rgba(255, 255, 255, 0.4)',
          lineWidth: 1,
        }
      })),
      edges: filteredData.edges?.map((l, i) => ({
        id: `edge-${i}`,
        source: typeof l.source === 'object' ? (l.source as any).id : l.source,
        target: typeof l.target === 'object' ? (l.target as any).id : l.target,
        data: {
          label: l.type || '',
        },
        style: {
          stroke: 'rgba(255, 255, 255, 0.15)',
          lineWidth: 1,
        }
      })) || []
    };

    // 2. 初始化图实例 (G6 v5.0)
    const graph = new Graph({
      container: containerRef.current,
      width: width || containerRef.current.clientWidth || 800,
      height: height || containerRef.current.clientHeight || 600,
      data: g6Data,
      layout: {
        type: 'gForce',
        gpuEnabled: true,
        workerEnabled: true,
        linkDistance: 120,
        nodeStrength: 1000,
        nodeSize: 30,
        preventOverlap: true,
      },
      plugins: [
        {
          type: 'edge-bundling',
          key: 'bundling',
          bundleThreshold: 0.6,
          K: 0.1,
          cycles: 6,
        },
      ],
      behaviors: ['drag-canvas', 'zoom-canvas', 'drag-node', 'click-select'],
      autoResize: true,
      node: {
        style: {
          labelPlacement: 'bottom',
          labelText: (d: any) => d.data.label,
          labelFontSize: 12,
          labelFill: token.colorText,
        }
      },
      edge: {
        type: 'flowing-edge', // 使用自定义流动边
        style: {
          endArrow: true,
          strokeOpacity: 0.2,
          lineDash: [4, 4], // 开启虚线模式
        }
      }
    });

    graphRef.current = graph;
    graph.render();

    // 3. 事件绑定
    graph.on('node:click', (evt: any) => {
      const { target } = evt;
      const nodeId = target.id;
      
      if (onNodeClick) {
          const nodeData = data.nodes.find(n => n.id === nodeId);
          if (nodeData) onNodeClick(nodeData);
      }
      
      // 聚焦动效 (v5.0 推荐方式)
      graph.zoomTo(1.5, { duration: 500 });
      graph.focusElement(nodeId, { duration: 500 });
    });

    return () => {
      graph.destroy();
    };
  }, [filteredData, width, height, token, onNodeClick]);

  return (
    <div className="g6-graph-wrapper" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="g6-graph-controls" style={{ padding: '8px 16px', background: 'rgba(255, 255, 255, 0.05)', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <Space size="middle">
          <Text type="secondary" style={{ fontSize: '12px' }}>显示节点类型:</Text>
          <Checkbox.Group 
            options={availableTypes} 
            value={selectedTypes} 
            onChange={(vals) => setSelectedTypes(vals as string[])} 
          />
        </Space>
      </div>
      <div 
        ref={containerRef} 
        className="g6-graph-container"
        style={{ 
          flex: 1,
          width: '100%', 
          minHeight: 400, 
          background: 'transparent',
          overflow: 'hidden'
        }} 
      />
    </div>
  );
};
