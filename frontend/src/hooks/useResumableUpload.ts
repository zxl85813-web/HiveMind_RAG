/**
 * useResumableUpload — S3 Multipart 断点续传 Hook
 *
 * 核心机制：
 *   1. 初始化时调用后端 /multipart/init，获取 upload_id + s3_key
 *   2. 将上传状态持久化到 localStorage（key = 文件指纹）
 *   3. 每个分片直接 PUT 到 S3 预签名 URL（后端不承受流量）
 *   4. 断网/刷新后，从 localStorage 恢复状态，跳过已完成分片
 *   5. 所有分片完成后调用 /multipart/complete 合并，创建 Document 记录
 *
 * 文件指纹（fingerprint）= filename + fileSize + lastModified
 * 用于在 localStorage 中唯一标识一个上传任务，即使文件名相同也能区分。
 *
 * 分片大小：5MB（S3 最小分片限制）
 * 并发分片：3 个同时上传（可配置）
 */

import { useCallback, useRef } from 'react';
import api from '../services/api';

// ── 类型 ──────────────────────────────────────────────────────────────────────

export interface UploadedPart {
  PartNumber: number;
  ETag: string;
}

export interface ResumableUploadState {
  fingerprint: string;
  filename: string;
  s3Key: string;
  uploadId: string;
  totalParts: number;
  chunkSize: number;
  fileSize: number;
  folderPath?: string;
  completedParts: UploadedPart[];   // 已成功上传的分片
  createdAt: number;                // 时间戳，用于清理过期记录
}

export interface ResumableUploadOptions {
  /** 每个分片上传进度回调 (0-100) */
  onProgress?: (percent: number, uploadedBytes: number, totalBytes: number) => void;
  /** 单个分片完成回调 */
  onPartComplete?: (partNumber: number, total: number) => void;
  /** 上传完成回调，返回 doc_id */
  onComplete?: (docId: string, s3Key: string) => void;
  /** 错误回调 */
  onError?: (error: Error, partNumber?: number) => void;
  /** 并发分片数，默认 3 */
  concurrency?: number;
  /** 分片大小（字节），默认 5MB */
  chunkSize?: number;
}

// ── 常量 ──────────────────────────────────────────────────────────────────────

const STORAGE_KEY_PREFIX = 'hm_resumable_upload_';
const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;   // 5MB
const DEFAULT_CONCURRENCY = 3;
const MAX_RETRY_PER_PART = 3;
/** localStorage 中保留上传记录的最长时间（7天），超过则清理 */
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

// ── 工具函数 ──────────────────────────────────────────────────────────────────

function getFingerprint(file: File): string {
  return `${file.name}_${file.size}_${file.lastModified}`;
}

function storageKey(fingerprint: string): string {
  return `${STORAGE_KEY_PREFIX}${fingerprint}`;
}

function saveState(state: ResumableUploadState): void {
  try {
    localStorage.setItem(storageKey(state.fingerprint), JSON.stringify(state));
  } catch {
    // localStorage 满了，忽略
  }
}

function loadState(fingerprint: string): ResumableUploadState | null {
  try {
    const raw = localStorage.getItem(storageKey(fingerprint));
    if (!raw) return null;
    const state: ResumableUploadState = JSON.parse(raw);
    // 清理过期记录
    if (Date.now() - state.createdAt > MAX_AGE_MS) {
      localStorage.removeItem(storageKey(fingerprint));
      return null;
    }
    return state;
  } catch {
    return null;
  }
}

function clearState(fingerprint: string): void {
  localStorage.removeItem(storageKey(fingerprint));
}

/** 清理所有超过 MAX_AGE_MS 的上传记录 */
export function cleanupExpiredUploads(): void {
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key?.startsWith(STORAGE_KEY_PREFIX)) continue;
    try {
      const raw = localStorage.getItem(key);
      if (!raw) continue;
      const state: ResumableUploadState = JSON.parse(raw);
      if (Date.now() - state.createdAt > MAX_AGE_MS) {
        keysToRemove.push(key);
      }
    } catch {
      keysToRemove.push(key!);
    }
  }
  keysToRemove.forEach(k => localStorage.removeItem(k));
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useResumableUpload() {
  /** 用于取消正在进行的上传 */
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * 检查文件是否有未完成的上传记录（用于 UI 提示"是否续传"）
   */
  const checkResumable = useCallback((file: File): ResumableUploadState | null => {
    return loadState(getFingerprint(file));
  }, []);

  /**
   * 取消当前上传（不清理 localStorage，下次可续传）
   */
  const cancelUpload = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  /**
   * 彻底放弃上传（清理 localStorage + 通知后端 abort）
   */
  const abortUpload = useCallback(async (file: File) => {
    abortControllerRef.current?.abort();
    const fingerprint = getFingerprint(file);
    const state = loadState(fingerprint);
    if (state) {
      try {
        await api.post('/knowledge/documents/multipart/abort', {
          s3_key: state.s3Key,
          upload_id: state.uploadId,
        });
      } catch { /* 忽略，后端会自动清理过期的 multipart */ }
      clearState(fingerprint);
    }
  }, []);

  /**
   * 核心上传函数
   *
   * @param file       要上传的文件
   * @param folderPath 文件夹路径（可选）
   * @param options    进度/完成/错误回调
   * @returns          doc_id（后端 Document.id）
   */
  const upload = useCallback(async (
    file: File,
    folderPath: string | undefined,
    options: ResumableUploadOptions = {},
  ): Promise<string> => {
    const {
      onProgress,
      onPartComplete,
      onComplete,
      onError,
      concurrency = DEFAULT_CONCURRENCY,
      chunkSize = DEFAULT_CHUNK_SIZE,
    } = options;

    const fingerprint = getFingerprint(file);
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // ── 1. 检查是否有可续传的状态 ──────────────────────────────────────────
    let state = loadState(fingerprint);
    let completedParts: UploadedPart[] = state?.completedParts ?? [];

    if (state) {
      // 有本地记录，向后端确认已上传的分片（防止 ETag 不一致）
      try {
        const partsRes = await api.post<{ data: Array<{ PartNumber: number; ETag: string }> }>(
          '/knowledge/documents/multipart/list-parts',
          { s3_key: state.s3Key, upload_id: state.uploadId, part_number: 1 }
        );
        const serverParts = partsRes.data?.data ?? [];
        // 以服务端为准，更新本地已完成分片
        completedParts = serverParts.map(p => ({ PartNumber: p.PartNumber, ETag: p.ETag }));
        state = { ...state, completedParts };
        saveState(state);
      } catch {
        // 服务端查询失败（upload_id 可能已过期），重新初始化
        state = null;
        completedParts = [];
        clearState(fingerprint);
      }
    }

    // ── 2. 初始化（或复用已有的 upload_id）────────────────────────────────
    if (!state) {
      const initRes = await api.post<{
        data: { upload_id: string; s3_key: string; chunk_size: number; total_parts: number }
      }>('/knowledge/documents/multipart/init', {
        filename: file.name,
        folder_path: folderPath,
        content_type: file.type || 'application/octet-stream',
        file_size: file.size,
      });

      const { upload_id, s3_key, chunk_size: serverChunkSize, total_parts } = initRes.data.data;
      state = {
        fingerprint,
        filename: file.name,
        s3Key: s3_key,
        uploadId: upload_id,
        totalParts: total_parts,
        chunkSize: serverChunkSize || chunkSize,
        fileSize: file.size,
        folderPath,
        completedParts: [],
        createdAt: Date.now(),
      };
      saveState(state);
    }

    const { s3Key, uploadId, totalParts, chunkSize: partSize } = state;
    const completedSet = new Set(completedParts.map(p => p.PartNumber));

    // ── 3. 计算待上传分片 ──────────────────────────────────────────────────
    const pendingParts: number[] = [];
    for (let i = 1; i <= totalParts; i++) {
      if (!completedSet.has(i)) pendingParts.push(i);
    }

    // 已上传字节数（用于进度计算）
    let uploadedBytes = completedParts.reduce((sum, p) => {
      const partIdx = p.PartNumber - 1;
      const start = partIdx * partSize;
      const end = Math.min(start + partSize, file.size);
      return sum + (end - start);
    }, 0);

    // ── 4. 并发上传分片 ────────────────────────────────────────────────────
    const allParts: UploadedPart[] = [...completedParts];

    const uploadPart = async (partNumber: number): Promise<void> => {
      if (controller.signal.aborted) throw new Error('Upload cancelled');

      const start = (partNumber - 1) * partSize;
      const end = Math.min(start + partSize, file.size);
      const blob = file.slice(start, end);

      // 获取预签名 URL
      const urlRes = await api.post<{ data: { url: string } }>(
        '/knowledge/documents/multipart/part-url',
        { s3_key: s3Key, upload_id: uploadId, part_number: partNumber }
      );
      const presignedUrl = urlRes.data.data.url;

      // 直接 PUT 到 S3（带重试）
      let lastError: Error | null = null;
      for (let attempt = 0; attempt < MAX_RETRY_PER_PART; attempt++) {
        if (controller.signal.aborted) throw new Error('Upload cancelled');
        try {
          const response = await fetch(presignedUrl, {
            method: 'PUT',
            body: blob,
            signal: controller.signal,
            headers: { 'Content-Type': file.type || 'application/octet-stream' },
          });

          if (!response.ok) {
            throw new Error(`S3 PUT failed: ${response.status} ${response.statusText}`);
          }

          // S3 在响应头中返回 ETag
          const etag = response.headers.get('ETag')?.replace(/"/g, '') ?? '';
          const part: UploadedPart = { PartNumber: partNumber, ETag: etag };

          // 更新本地状态
          allParts.push(part);
          uploadedBytes += end - start;
          state!.completedParts = [...allParts];
          saveState(state!);

          onPartComplete?.(partNumber, totalParts);
          onProgress?.(
            Math.round((uploadedBytes / file.size) * 100),
            uploadedBytes,
            file.size,
          );
          return;
        } catch (err: any) {
          lastError = err;
          if (err.name === 'AbortError') throw err;
          // 指数退避重试
          await new Promise(r => setTimeout(r, 500 * Math.pow(2, attempt)));
        }
      }
      throw lastError ?? new Error(`Part ${partNumber} failed after ${MAX_RETRY_PER_PART} retries`);
    };

    // 信号量控制并发
    const semaphore = async (tasks: (() => Promise<void>)[], limit: number) => {
      const results: Promise<void>[] = [];
      let i = 0;
      const run = async (): Promise<void> => {
        while (i < tasks.length) {
          const task = tasks[i++];
          await task();
        }
      };
      for (let w = 0; w < Math.min(limit, tasks.length); w++) {
        results.push(run());
      }
      await Promise.all(results);
    };

    try {
      await semaphore(
        pendingParts.map(pn => () => uploadPart(pn)),
        concurrency,
      );
    } catch (err: any) {
      onError?.(err);
      throw err;
    }

    // ── 5. 合并分片，创建 Document 记录 ───────────────────────────────────
    // 按 PartNumber 排序（S3 要求）
    const sortedParts = allParts
      .sort((a, b) => a.PartNumber - b.PartNumber)
      .map(p => ({ PartNumber: p.PartNumber, ETag: p.ETag }));

    const completeRes = await api.post<{ data: { id: string } }>(
      '/knowledge/documents/multipart/complete',
      {
        s3_key: s3Key,
        upload_id: uploadId,
        filename: file.name,
        file_size: file.size,
        file_type: file.name.split('.').pop()?.toLowerCase() ?? 'unknown',
        folder_path: folderPath,
        parts: sortedParts,
      }
    );

    const docId = completeRes.data.data.id;

    // 清理 localStorage
    clearState(fingerprint);

    onProgress?.(100, file.size, file.size);
    onComplete?.(docId, s3Key);

    return docId;
  }, []);

  return { upload, cancelUpload, abortUpload, checkResumable };
}
