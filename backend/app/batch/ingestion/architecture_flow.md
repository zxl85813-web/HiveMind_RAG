```mermaid
graph TD
    %% --- 入口 & 批处理管理 ---
    Input[📂 批量上传目录/Zip] --> BatchMgr{⚡ Batch Manager}
    BatchMgr -->|1. 任务拆分| Queue[📋 Task Queue (MySQL)]
    
    %% --- 并发执行 Worker Pool ---
    Queue -->|调度| Worker1[Worker Thread 1]
    Queue -->|调度| Worker2[Worker Thread 2]
    Queue -->|调度| Worker3[Worker Thread ...]

    %% --- 灵活的 Pipeline (插件化架构) ---
    subgraph "The Flexible Pipeline (Plugins)"
        direction TB
        
        %% Stage 1: 动态路由
        Worker1 --> Router[🤖 Router Agent]
        Router -->|Type=Excel设计书| ExcelParser[🔌 Excel Plugin]
        Router -->|Type=Java代码| CodeParser[🔌 Java AST Plugin]
        Router -->|Type=PDF文档| MinerUParser[🔌 MinerU Plugin]
        Router -.->|New Type?| NewPlugin[✨ 只需注册新插件]

        %% Stage 2: 标准化
        ExcelParser --> Standardizer[📦 Standardized Resource Protocol]
        CodeParser --> Standardizer
        MinerUParser --> Standardizer

        %% Stage 3: AI 增强 (可插拔的功能链)
        Standardizer --> AIEngine[🧠 AI Enrichment Swarm]
        AIEngine -->|Parallel| Summarizer[📝 摘要生成]
        AIEngine -->|Parallel| Tagger[🏷️ 业务打标 (Freestyle)]
        AIEngine -->|Parallel| GraphBuilder[🕸️ 图谱构建]
    end

    %% --- 存储层 ---
    Summarizer --> Storage{💾 Storage Gateway}
    Tagger --> Storage
    GraphBuilder --> Storage

    Storage -->|Write| Neo4j[(Neo4j 知识图谱)]
    Storage -->|Write| ES[(ElasticSearch 向量)]
    Storage -->|Update| StateDB[(MySQL 状态库)]

    %% --- 扩展性说明 ---
    classDef plugin fill:#f9f,stroke:#333,stroke-width:2px;
    class ExcelParser,CodeParser,MinerUParser,NewPlugin plugin;
    class Summarizer,Tagger,GraphBuilder plugin;
```

## 核心灵活性设计 (How it stays flexible)

这个架构的**灵活**体现在它是**基于注册表 (Registry-based)** 的，而不是硬编码的。

### 1. 怎么"不停添加各种功能"？
我们不写死 `if type == 'excel': do_excel()`。而是使用**装饰器模式**。

当你想要支持一种新文件（比如 `GoLang` 代码）时，你**不需要修改核心 Pipeline 代码**，只需要加一个文件：

```python
# backend/app/batch/plugins/golang_parser.py

@parser_registry.register(resource_type="golang_source")
def parse_golang(content: str) -> StandardizedResource:
    # 你的解析逻辑...
    return standardized_data
```

系统启动时会自动扫描 `plugins/` 目录，下一秒 Router 就能识别并处理 Go 语言代码了。

### 2. 怎么"批量处理"？
请看顶部的 `Batch Manager` 和 `Task Queue`。
-   **Task Queue (MySQL)**: 保证即使有 10,000 个文件，也不会撑爆内存。它们会乖乖排队。
-   **Worker Pool**: 你可以配置 `CONCURRENCY = 5` 或 `50`，根据你的机器性能灵活调整处理速度。
-   **状态持久化**: 每个文件的处理状态（Pending, Parsed, Enriched, Saved）都存在 MySQL 里。如果机器断电，重启后会从断点继续跑，不需要重头开始。

### 3. Agent 的介入
在 `AI Enrichment` 阶段，我们可以挂载任意多个 Agent。
-   今天你想加个“安全漏洞扫描”功能？
-   写一个 `SecurityAgent`，注册到 Enrichment Stage。
-   Pipeline 会自动把数据喂给它，并把结果存入 ES 的 `freestyle.security_risks` 字段。
