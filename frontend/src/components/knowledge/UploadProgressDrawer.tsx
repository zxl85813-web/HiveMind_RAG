/**
 * UploadProgressDrawer — 文档批量上传进度面板
 *
 * 功能：
 *   - 展示每个文件的上传状态（等待 / 上传中 / 处理中 / 完成 / 失败）
 *   - 通过 SSE 实时接收后端 Celery 处理进度
 *   - 整体进度条 + 文件列表动画
 *
 * 动画策略：
 *   - 文件行入场：fadeInUp（错开 50ms stagger）
 *   - 状态变更：scale + color transition（CSS transition）
 *   - 进度条：Ant Design Progress 自带 transition
 *   - 完成时：confetti-like pulse on the progress bar
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Drawer, Progress, List, Tag, Typography, Space, Button, Tooltip, Badge
} from 'antd';
import {
  CheckCircleFilled, CloseCircleFilled, LoadingOutlined,
  ClockCircleOutlined, FileOutlined, ThunderboltOutlined, ReloadOutlined
} from '@ant-design/icons';
import { useSSE } from '../../hooks/useSSE';
import { tokenVault } from '../../core/auth/TokenVault';

const { Text } = Typography;

// ── 类型 ──────────────────────────────────────────────────────────────────────

export type FileUploadStatus =
  | 'waiting'      // 等待上传到 S3
  | 'uploading'    // 正在上传到 S3
  | 'processing'   // 已入队，Celery 处理中
  | 'done'         // 处理完成
  | 'failed'       // 失败
  | 'resumable';   // 有未完成的上传记录，可续传

export interface UploadFileItem {
  uid: string;           // 前端唯一 ID
  filename: string;
  folderPath?: string;
  fileSize: number;
  status: FileUploadStatus;
  docId?: string;        // 后端 Document.id（上传成功后填入）
  errorMsg?: string;
  /** 0-100，仅 uploading 阶段有意义 */
  uploadPercent?: number;
}

interface BatchProgress {
  total: number;
  completed: number;
  failed: number;
  percent: number;
  status: 'processing' | 'completed' | 'partial_failed';
}

interface Props {
  open: boolean;
  onClose: () => void;
  files: UploadFileItem[];
  batchId?: string;       // 后端 batch_id，有值时开启 SSE 订阅
  onFileStatusChange?: (uid: string, status: FileUploadStatus, docId?: string) => void;
}

// ── 辅助：状态图标 ─────────────────────────────────────────────────────────────

const StatusIcon: React.FC<{ status: FileUploadStatus }> = ({ status }) => {
  switch (status) {
    case 'done':
      return <CheckCircleFilled style={{ color: 'var(--hm-color-success, #06d6a0)', fontSize: 16 }} />;
    case 'failed':
      return <CloseCircleFilled style={{ color: 'var(--hm-color-error, #ef476f)', fontSize: 16 }} />;
    case 'uploading':
    case 'processing':
      return <LoadingOutlined style={{ color: 'var(--hm-color-brand, #06d6a0)', fontSize: 16 }} spin />;
    case 'resumable':
      return <ReloadOutlined style={{ color: 'var(--hm-color-warning, #ffd166)', fontSize: 16 }} />;
    default:
      return <ClockCircleOutlined style={{ color: 'var(--hm-color-text-secondary, #888)', fontSize: 16 }} />;
  }
};

const StatusTag: React.FC<{ status: FileUploadStatus }> = ({ status }) => {
  const map: Record<FileUploadStatus, { color: string; label: string }> = {
    waiting:    { color: 'default',    label: '等待中' },
    uploading:  { color: 'processing', label: '上传中' },
    processing: { color: 'blue',       label: '处理中' },
    done:       { color: 'success',    label: '完成' },
    failed:     { color: 'error',      label: '失败' },
    resumable:  { color: 'warning',    label: '可续传' },
  };
  const { color, label } = map[status];
  return <Tag color={color} style={{ transition: 'all 0.3s ease' }}>{label}</Tag>;
};

// ── 主组件 ────────────────────────────────────────────────────────────────────

export const UploadProgressDrawer: React.FC<Props> = ({
  open, onClose, files, batchId, onFileStatusChange
}) => {
  const token = tokenVault.getAccessToken();
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  // 用 Map 追踪每个 doc_id → uid 的映射，SSE 事件只有 doc_id
  const docIdToUidRef = useRef<Map<string, string>>(new Map());

  // 当 files 更新时，维护 docId → uid 映射
  useEffect(() => {
    files.forEach(f => {
      if (f.docId) docIdToUidRef.current.set(f.docId, f.uid);
    });
  }, [files]);

  // ── SSE 进度订阅 ────────────────────────────────────────────────────────────
  const handleSSEMessage = useCallback((data: any, eventType: string) => {
    if (!data) return;

    // 更新批次整体进度
    if (data.total !== undefined) {
      setBatchProgress({
        total: data.total,
        completed: data.completed,
        failed: data.failed,
        percent: data.percent,
        status: data.status,
      });
    }

    // 更新单文件状态
    if (eventType === 'file_done' && data.doc_id) {
      const uid = docIdToUidRef.current.get(data.doc_id);
      if (uid) onFileStatusChange?.(uid, 'done', data.doc_id);
    }
    if (eventType === 'file_failed' && data.doc_id) {
      const uid = docIdToUidRef.current.get(data.doc_id);
      if (uid) onFileStatusChange?.(uid, 'failed', data.doc_id);
    }
  }, [onFileStatusChange]);

  const sseUrl = batchId
    ? `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/knowledge/batches/${batchId}/progress`
    : '';

  const { connect, disconnect, isConnected } = useSSE({
    url: sseUrl,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    onMessage: handleSSEMessage,
  });

  // batchId 出现时自动连接 SSE
  useEffect(() => {
    if (batchId && open) {
      connect();
    }
    return () => { disconnect(); };
  }, [batchId, open]);

  // 批次完成后断开 SSE
  useEffect(() => {
    if (batchProgress?.status === 'completed' || batchProgress?.status === 'partial_failed') {
      disconnect();
    }
  }, [batchProgress?.status]);

  // ── 统计 ────────────────────────────────────────────────────────────────────
  const total = files.length;
  const doneCount = files.filter(f => f.status === 'done').length;
  const failedCount = files.filter(f => f.status === 'failed').length;
  const processingCount = files.filter(f => f.status === 'processing' || f.status === 'uploading').length;

  // 优先用 SSE 推送的精确进度，否则用前端本地计数
  const percent = batchProgress
    ? batchProgress.percent
    : total > 0 ? Math.round((doneCount / total) * 100) : 0;

  const isAllDone = total > 0 && (doneCount + failedCount) >= total;
  const progressStatus = failedCount > 0 && isAllDone
    ? 'exception'
    : isAllDone ? 'success' : 'active';

  // ── 渲染 ────────────────────────────────────────────────────────────────────
  return (
    <Drawer
      title={
        <Space>
          <ThunderboltOutlined style={{ color: 'var(--hm-color-brand, #06d6a0)' }} />
          <span>上传进度</span>
          {isConnected && (
            <Badge status="processing" text={
              <Text type="secondary" style={{ fontSize: 12 }}>实时同步中</Text>
            } />
          )}
        </Space>
      }
      open={open}
      onClose={onClose}
      width={480}
      footer={
        <div style={{ textAlign: 'right' }}>
          <Button onClick={onClose} disabled={processingCount > 0 && !isAllDone}>
            {isAllDone ? '关闭' : '后台处理中...'}
          </Button>
        </div>
      }
    >
      {/* 整体进度条 */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <Text strong>整体进度</Text>
          <Space size={4}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {doneCount}/{total} 完成
            </Text>
            {failedCount > 0 && (
              <Text type="danger" style={{ fontSize: 12 }}>
                · {failedCount} 失败
              </Text>
            )}
          </Space>
        </div>
        <Progress
          percent={percent}
          status={progressStatus}
          strokeColor={
            progressStatus === 'active'
              ? { from: '#06d6a0', to: '#118ab2' }
              : undefined
          }
          style={{
            // 完成时触发 pulse 动画
            animation: isAllDone && failedCount === 0
              ? 'pulseGlow 1.5s ease-in-out 3'
              : undefined,
          }}
        />
      </div>

      {/* 文件列表 */}
      <List
        dataSource={files}
        renderItem={(item, index) => (
          <List.Item
            key={item.uid}
            style={{
              // stagger 入场动画
              animation: `fadeInUp 0.3s ease both`,
              animationDelay: `${Math.min(index * 40, 400)}ms`,
              padding: '10px 0',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
              transition: 'background 0.2s ease',
            }}
          >
            <List.Item.Meta
              avatar={
                <div style={{ paddingTop: 2 }}>
                  <StatusIcon status={item.status} />
                </div>
              }
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileOutlined style={{ color: 'var(--hm-color-text-secondary, #888)', fontSize: 12 }} />
                  <Tooltip title={item.folderPath ? `${item.folderPath}/${item.filename}` : item.filename}>
                    <Text
                      ellipsis
                      style={{
                        maxWidth: 220,
                        fontSize: 13,
                        // 完成时颜色过渡
                        color: item.status === 'done'
                          ? 'var(--hm-color-success, #06d6a0)'
                          : item.status === 'failed'
                          ? 'var(--hm-color-error, #ef476f)'
                          : 'var(--hm-color-text-primary, #fff)',
                        transition: 'color 0.4s ease',
                      }}
                    >
                      {item.filename}
                    </Text>
                  </Tooltip>
                  <StatusTag status={item.status} />
                </div>
              }
              description={
                <div style={{ marginTop: 4 }}>
                  {/* 上传进度子条（仅 uploading 阶段） */}
                  {item.status === 'uploading' && item.uploadPercent !== undefined && (
                    <Progress
                      percent={item.uploadPercent}
                      size="small"
                      showInfo={false}
                      strokeColor="var(--hm-color-brand, #06d6a0)"
                      style={{ marginBottom: 4 }}
                    />
                  )}
                  <Space size={4} wrap>
                    {item.folderPath && (
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        📁 {item.folderPath}
                      </Text>
                    )}
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {(item.fileSize / 1024).toFixed(1)} KB
                    </Text>
                    {item.errorMsg && (
                      <Text type="danger" style={{ fontSize: 11 }}>
                        {item.errorMsg}
                      </Text>
                    )}
                  </Space>
                </div>
              }
            />
          </List.Item>
        )}
        locale={{ emptyText: '暂无文件' }}
      />
    </Drawer>
  );
};
