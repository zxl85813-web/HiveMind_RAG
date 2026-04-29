/**
 * apiTypes — 后端 OpenAPI 模型的友好别名导出。
 *
 * 不要在业务代码里直接 import `./api.gen.ts`，而是通过本文件按需重导出。
 * 这样：
 *   - 业务侧只看到稳定、易读的类型名 (KnowledgeBase, ChatRequest, ...)
 *   - 后端 schema 改名时只需改这一个文件
 *
 * 重新生成: `npm run gen:api`
 */
import type { components, paths, operations } from './api.gen';

// ── 原生命空间（高级用法可直接使用）────────────────────────
export type { paths, operations, components };
export type Schemas = components['schemas'];

// ── 常用 Schema 别名（按字母序）─────────────────────────────
export type ApiResponse = Schemas['ApiResponse'];
export type AuditLogRead = Schemas['AuditLogRead'];
export type BadCase = Schemas['BadCase'];
export type BadCaseUpdate = Schemas['BadCaseUpdate'];
export type ChatRequest = Schemas['ChatRequest'];
export type ConversationListItem = Schemas['ConversationListItem'];
export type CreateBatchJobRequest = Schemas['CreateBatchJobRequest'];
export type DesensitizationPolicyCreate = Schemas['DesensitizationPolicyCreate'];
export type DesensitizationPolicyRead = Schemas['DesensitizationPolicyRead'];
export type DesensitizationReportRead = Schemas['DesensitizationReportRead'];
export type Document = Schemas['Document'];
export type DocumentPermissionCreate = Schemas['DocumentPermissionCreate'];
export type DocumentPermissionRead = Schemas['DocumentPermissionRead'];
export type DocumentResponse = Schemas['DocumentResponse'];
export type DocumentReviewRead = Schemas['DocumentReviewRead'];
export type DocumentReviewUpdate = Schemas['DocumentReviewUpdate'];
export type DocumentTagAttach = Schemas['DocumentTagAttach'];
export type EvaluationReport = Schemas['EvaluationReport'];
export type EvaluationRun = Schemas['EvaluationRun'];
export type EvaluationSet = Schemas['EvaluationSet'];
export type FAQItem = Schemas['FAQItem'];
export type FineTuningCreate = Schemas['FineTuningCreate'];
export type FineTuningItem = Schemas['FineTuningItem'];
export type GenerateRequest = Schemas['GenerateRequest'];
export type GenerateResponse = Schemas['GenerateResponse'];
export type HITLTask = Schemas['HITLTask'];
export type KBPermissionInput = Schemas['KBPermissionInput'];
export type KBStatus = Schemas['KBStatus'];
export type KnowledgeBase = Schemas['KnowledgeBase'];
export type KnowledgeBaseCreate = Schemas['KnowledgeBaseCreate'];
export type KnowledgeBaseDocumentLink = Schemas['KnowledgeBaseDocumentLink'];
export type KnowledgeBasePermission = Schemas['KnowledgeBasePermission'];
export type PipelineConfig = Schemas['PipelineConfig'];
export type PipelineConfigRequest = Schemas['PipelineConfigRequest'];
export type PlatformFeature = Schemas['PlatformFeature'];
export type PlatformKnowledge = Schemas['PlatformKnowledge'];
export type SearchRequest = Schemas['SearchRequest'];
export type SearchResponse = Schemas['SearchResponse'];
export type SensitiveItemRead = Schemas['SensitiveItemRead'];
export type TagCategoryCreate = Schemas['TagCategoryCreate'];
export type TagCategoryRead = Schemas['TagCategoryRead'];
export type TagCreate = Schemas['TagCreate'];
export type TagRead = Schemas['TagRead'];
export type TagWithCategory = Schemas['TagWithCategory'];
export type TestsetCreate = Schemas['TestsetCreate'];

// ── ApiResponse 泛型外壳（便于业务侧直接使用 ApiResp<T>）────
/**
 * 通用响应包装，与后端 ApiResponse[T] 对齐。
 * 用法：`type R = ApiResp<KnowledgeBase>`
 */
export interface ApiResp<T> {
    code: number;
    message: string;
    data?: T | null;
    error?: string | null;
}
