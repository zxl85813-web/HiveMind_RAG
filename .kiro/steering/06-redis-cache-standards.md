---
description: Redis 与缓存开发规范 — 编辑 Redis/缓存相关文件时自动加载
inclusion: fileMatch
fileMatchPattern: "**/redis.py,**/cache_service.py,**/cache*.py,**/celery*.py"
---

# Redis 与缓存开发规范

编辑 Redis 或缓存相关代码时，必须遵守以下规范。

## 核心约束

### 连接与访问
- 统一通过 `get_redis_client()` 工厂方法获取客户端，禁止直接实例化 Redis
- 工厂方法位于 `backend/app/core/redis.py`
- 配置项: `REDIS_URL`（从 `app.core.config.settings` 读取，默认 `redis://localhost:6379/0`）

### 降级保护（强制）
- Redis 不可用时必须自动降级到 `MockRedis`（内存字典），禁止让系统崩溃
- `get_redis_client()` 已内置 2 次重试 + 自动降级逻辑
- 连接超时设为 3s（`socket_connect_timeout=3`），防止网络抖动误降级

### 链路追踪
- 生产环境使用 `TraceableRedis`（继承自 `redis.Redis`），自动注入 `trace_id`
- 所有 Redis 错误必须通过 `loguru.logger` 记录，包含 trace_id 上下文

### 语义缓存（CacheService）
- 位于 `backend/app/services/cache_service.py`
- 使用向量搜索查找语义相似的已回答问题
- 相似度阈值: `0.96`（语义缓存）/ `0.92`（路由缓存）
- TTL: 语义缓存 24h / 路由缓存 1h
- 必须检测并拒绝"投毒条目"（`POISON_TOKENS`）和"回声条目"

### Redis 用途分类
| 用途 | 说明 | 注意事项 |
|------|------|----------|
| 语义缓存 | 向量相似度匹配已回答问题 | 高阈值 0.96，带 TTL |
| 工作记忆 | L1 会话级临时状态 | 当前用 Python dict，计划迁移 Redis |
| 事件总线 | WriteEventBus / Blackboard Pub/Sub | 集群通信用 |
| 任务队列 | Celery worker 后端 | 速率限制配置在图谱中 |

### 开发环境
- 本地未安装 Redis 时，`MockRedis` 自动接管，使用内存字典模拟
- MockRedis 仅支持基础操作（get/set/rpush/rpop/ping），复杂命令返回 None
- 日志会输出 `⚠️ [Redis] No physical Redis found. Using IN-MEMORY MOCK.` 提醒

### 禁止事项
- 禁止在业务代码中直接 `import redis` 并手动创建连接
- 禁止在缓存中存储未经安全检查的 LLM 输出（必须过 POISON_TOKENS 过滤）
- 禁止硬编码 Redis URL，必须通过 `settings.REDIS_URL` 获取
