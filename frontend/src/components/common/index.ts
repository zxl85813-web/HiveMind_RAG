/**
 * 通用组件统一导出。
 *
 * 使用:
 *   import { PageContainer, StatCard, EmptyState, StatusTag } from '@/components/common';
 *
 * @module components/common
 */

export { AppLayout } from './AppLayout';
export { PageContainer } from './PageContainer';
export type { PageContainerProps } from './PageContainer';
export { StatCard } from './StatCard';
export type { StatCardProps } from './StatCard';
export { EmptyState } from './EmptyState';
export type { EmptyStateProps } from './EmptyState';
export { StatusTag } from './StatusTag';
export type { StatusTagProps } from './StatusTag';
export { ErrorDisplay } from './ErrorDisplay';
export type { ErrorDisplayProps } from './ErrorDisplay';
export { LoadingState } from './LoadingState';
export type { LoadingStateProps } from './LoadingState';
export { ConfirmAction } from './ConfirmAction';
export type { ConfirmActionProps } from './ConfirmAction';
export { PermissionGuard, PermissionButton } from './PermissionGuard';
export { ErrorBoundary } from './ErrorBoundary';
