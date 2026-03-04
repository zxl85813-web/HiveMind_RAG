# REQ-010: 数据脱敏体系 (Data Desensitization / PII Protection)

> 📅 创建时间: 2026-02-22
> 📝 来源: 用户需求讨论
> 🏷️ 优先级: P1 — 安全合规

---

## 1. 需求背景

知识库中可能包含大量敏感信息（个人隐私、商业机密、内部密码等）。在以下环节都需要脱敏处理：

| 环节 | 风险 | 示例 |
|------|------|------|
| **文档上传** | 用户上传含敏感信息的原始文档 | 身份证号、银行卡号、手机号 |
| **分块索引** | 敏感信息被切入 Chunk 存入向量库 | 合同金额、密码、API Key |
| **LLM 调用** | 敏感数据被发送给第三方 LLM API | 客户姓名、地址被传给 OpenAI |
| **检索回答** | AI 回答中直接暴露敏感信息 | "张三的身份证号是 320xxx..." |
| **日志记录** | 敏感信息出现在系统日志中 | 请求日志中暴露 Token |

---

## 2. 敏感数据分类

### 2.1 个人身份信息 (PII)

| 类型代码 | 名称 | 示例 | 正则匹配 | 优先级 |
|---------|------|------|---------|--------|
| `PII_PHONE` | 手机号 | 13812345678 | `1[3-9]\d{9}` | P1 |
| `PII_IDCARD` | 身份证号 | 320106199001011234 | `\d{17}[\dXx]` | P1 |
| `PII_BANKCARD` | 银行卡号 | 6222021234567890123 | `\d{16,19}` | P1 |
| `PII_EMAIL` | 电子邮箱 | user@example.com | RFC 5322 | P1 |
| `PII_NAME` | 中文姓名 | 张三 | NER 模型 | P2 |
| `PII_ADDRESS` | 地址 | 北京市朝阳区xxx | NER 模型 | P2 |
| `PII_PASSPORT` | 护照号 | E12345678 | `[A-Z]\d{8}` | P2 |
| `PII_PLATE` | 车牌号 | 京A12345 | `[\u4e00-\u9fa5][A-Z][A-Z0-9]{5}` | P3 |

### 2.2 商业敏感信息 (BSI)

| 类型代码 | 名称 | 示例 | 检测方式 |
|---------|------|------|---------|
| `BSI_AMOUNT` | 合同金额 | ¥1,234,567.89 | 正则 + 上下文 |
| `BSI_SALARY` | 薪资信息 | 月薪 25000 元 | 关键词 + 金额 |
| `BSI_PASSWORD` | 密码 | password: abc123 | 关键词匹配 |
| `BSI_APIKEY` | API 密钥 | sk-xxxxxxxxxxxx | 前缀匹配 |
| `BSI_INTERNAL_IP` | 内网 IP | 192.168.1.100 | 私有 IP 段 |
| `BSI_DB_CONN` | 数据库连接串 | postgresql://user:pwd@host | URI 模式 |

### 2.3 安全等级

| 等级 | 标记 | 描述 | 脱敏策略 |
|------|------|------|---------|
| L1 公开 | 🟢 | 可公开的非敏感信息 | 不脱敏 |
| L2 内部 | 🟡 | 内部使用，低风险 | 可选脱敏 |
| L3 保密 | 🟠 | 含 PII 或商业秘密 | 强制脱敏 |
| L4 机密 | 🔴 | 高度敏感，合规要求 | 强制脱敏 + 审批访问 |

---

## 3. 脱敏策略

### 3.1 脱敏方法矩阵

| 方法 | 原理 | 可逆性 | 适用场景 |
|------|------|--------|---------|
| **掩码替换** | `138****5678` | ❌ 不可逆 | 手机号、身份证等定长数据 |
| **星号覆盖** | `张*` / `张**` | ❌ 不可逆 | 姓名 |
| **哈希替换** | `[PII:a3b2c1]` | 🟡 可反查 | 需追溯原文时 |
| **占位符替换** | `[PHONE_001]` | ✅ 可逆 | 需要保持文档结构 |
| **加密存储** | AES-256 加密 | ✅ 可逆 | 合规要求保留原文 |
| **泛化处理** | `25岁` → `20-30岁` | ❌ 不可逆 | 年龄、金额范围 |
| **完全删除** | 直接移除 | ❌ 不可逆 | 密码、API Key |

### 3.2 按数据类型推荐策略

```python
DEFAULT_STRATEGIES = {
    "PII_PHONE":    {"method": "mask",    "pattern": "{prefix}****{suffix4}"},
    "PII_IDCARD":   {"method": "mask",    "pattern": "{prefix6}********{suffix4}"},
    "PII_BANKCARD": {"method": "mask",    "pattern": "{prefix4} **** **** {suffix4}"},
    "PII_EMAIL":    {"method": "mask",    "pattern": "{first2}***@{domain}"},
    "PII_NAME":     {"method": "star",    "keep_first": True},
    "PII_ADDRESS":  {"method": "placeholder", "tag": "[ADDRESS]"},
    "BSI_PASSWORD": {"method": "delete"},
    "BSI_APIKEY":   {"method": "delete"},
    "BSI_AMOUNT":   {"method": "generalize", "precision": "万元"},
    "BSI_DB_CONN":  {"method": "delete"},
}
```

---

## 4. 系统架构

### 4.1 脱敏处理管道

```
文档上传
    ↓
[Stage 1: 扫描检测]
    - 正则匹配器 (PII_PHONE, PII_IDCARD, ...)
    - NER 模型 (PII_NAME, PII_ADDRESS)
    - 关键词匹配器 (BSI_PASSWORD, BSI_APIKEY)
    ↓
[Stage 2: 生成脱敏报告]
    - 找到 N 个敏感项
    - 按类型分类
    - 生成 SensitivityReport (存入数据库)
    ↓
[Stage 3: 决策路由]
    ├── 自动脱敏 (L3/L4 级别 → 按预设策略替换)
    ├── 人工确认 (L2 级别 → 进入审核台, 由人工确认是否脱敏)
    └── 放行 (L1 级别 → 不脱敏)
    ↓
[Stage 4: 执行脱敏]
    - 生成脱敏后文本
    - 保留原文映射表 (可选: 加密存储)
    ↓
[Stage 5: 脱敏后数据入库]
    - 脱敏后文本 → 分块 → 向量化
    - 原始文件标记为 "已脱敏" / "待脱敏" / "无需脱敏"
```

### 4.2 脱敏时机

| 时机 | 处理 | 说明 |
|------|------|------|
| **上传时** | 扫描 + 标记 | 识别敏感信息并生成报告 |
| **索引时** | 脱敏 + 向量化 | 脱敏后的文本存入向量库 |
| **LLM 调用时** | 二次过滤 | Prompt 中的敏感信息替换为占位符 |
| **回答展示时** | 输出过滤 | 检查 LLM 回答是否泄露敏感数据 |
| **日志记录时** | 日志清洗 | 自动过滤日志中的敏感信息 |

---

## 5. 数据模型

```python
class SensitiveItem(SQLModel, table=True):
    """单条敏感信息检测记录"""
    __tablename__ = "sensitive_items"
    
    id: str
    document_id: str            # FK -> documents.id
    item_type: str              # PII_PHONE | PII_IDCARD | BSI_AMOUNT ...
    original_value: str         # 加密存储的原始值
    masked_value: str           # 脱敏后的值
    position_start: int         # 在原始文本中的起始位置
    position_end: int           # 在原始文本中的结束位置
    chunk_id: str | None        # 属于哪个分块
    confidence: float = 1.0     # 检测置信度
    strategy_used: str          # 使用的脱敏策略
    status: str = "detected"    # detected | masked | reviewed | whitelisted
    reviewed_by: str | None     # 人工审核人
    created_at: datetime

class DesensitizationPolicy(SQLModel, table=True):
    """脱敏策略配置"""
    __tablename__ = "desensitization_policies"
    
    id: str
    kb_id: str | None           # 关联到特定知识库 (None = 全局)
    item_type: str              # PII_PHONE | PII_IDCARD ...
    method: str                 # mask | star | placeholder | delete | encrypt
    config: str                 # JSON — 方法特定参数
    security_level: str = "L3"  # L1 | L2 | L3 | L4
    auto_apply: bool = True     # 是否自动应用
    enabled: bool = True
    created_at: datetime
    updated_at: datetime

class DesensitizationReport(SQLModel, table=True):
    """文档级脱敏报告"""
    __tablename__ = "desensitization_reports"
    
    id: str
    document_id: str
    total_items: int = 0
    items_by_type: str = "{}"   # JSON {"PII_PHONE": 3, "PII_IDCARD": 1}
    items_masked: int = 0
    items_whitelisted: int = 0
    items_pending: int = 0
    security_level: str = "L1"  # 文档最终安全等级
    status: str = "pending"     # pending | completed | needs_review
    created_at: datetime
```

---

## 6. 核心服务接口

```python
class DesensitizationService:
    """数据脱敏服务"""
    
    async def scan_document(self, doc_id: str, text: str) -> DesensitizationReport:
        """扫描文档中的敏感信息"""
        
    async def apply_masking(self, doc_id: str, policy_id: str = None) -> str:
        """按策略执行脱敏，返回脱敏后文本"""
        
    async def filter_llm_context(self, text: str) -> str:
        """过滤即将发送给 LLM 的上下文"""
        
    async def filter_llm_output(self, text: str) -> str:
        """过滤 LLM 输出中可能泄露的敏感信息"""
        
    async def whitelist_item(self, item_id: str, reviewer_id: str):
        """人工标记为非敏感 (白名单)"""
```

---

## 7. 检测器注册中心

```python
class BaseDetector(abc.ABC):
    """敏感信息检测器基类"""
    item_type: str  # e.g. "PII_PHONE"
    
    @abc.abstractmethod
    def detect(self, text: str) -> List[DetectedItem]:
        """检测文本中的敏感信息"""
        pass

class DetectorRegistry:
    """检测器注册中心 — 支持自定义扩展"""
    _detectors: List[Type[BaseDetector]] = []
    
    @classmethod
    def register(cls, detector_cls):
        cls._detectors.append(detector_cls)
        return detector_cls
    
    @classmethod
    def scan(cls, text: str) -> List[DetectedItem]:
        results = []
        for det_cls in cls._detectors:
            det = det_cls()
            results.extend(det.detect(text))
        return results

# 内置检测器
@DetectorRegistry.register
class PhoneDetector(BaseDetector):
    item_type = "PII_PHONE"
    def detect(self, text):
        import re
        return [DetectedItem(type=self.item_type, value=m.group(), start=m.start(), end=m.end())
                for m in re.finditer(r'1[3-9]\d{9}', text)]

@DetectorRegistry.register
class IDCardDetector(BaseDetector):
    item_type = "PII_IDCARD"
    def detect(self, text):
        import re
        return [DetectedItem(type=self.item_type, value=m.group(), start=m.start(), end=m.end())
                for m in re.finditer(r'\d{17}[\dXx]', text)]

@DetectorRegistry.register
class APIKeyDetector(BaseDetector):
    item_type = "BSI_APIKEY"
    def detect(self, text):
        import re
        patterns = [
            r'sk-[a-zA-Z0-9]{20,}',           # OpenAI / SiliconFlow
            r'[A-Za-z0-9+/=]{32,}',           # Base64-like keys
            r'(?:api[_-]?key|token)\s*[:=]\s*\S+',  # key=value patterns
        ]
        results = []
        for p in patterns:
            for m in re.finditer(p, text, re.IGNORECASE):
                results.append(DetectedItem(type=self.item_type, value=m.group(), start=m.start(), end=m.end()))
        return results
```

---

## 8. API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/knowledge/desensitization/policies` | 获取脱敏策略列表 |
| POST | `/knowledge/desensitization/policies` | 创建/更新脱敏策略 |
| GET | `/knowledge/documents/{id}/sensitivity-report` | 获取文档脱敏报告 |
| POST | `/knowledge/documents/{id}/scan` | 手动触发敏感信息扫描 |
| POST | `/knowledge/documents/{id}/mask` | 手动触发脱敏执行 |
| POST | `/knowledge/sensitive-items/{id}/whitelist` | 白名单标记 |
| GET | `/knowledge/desensitization/stats` | 全局脱敏统计 |

---

## 9. 前端界面

### 9.1 脱敏策略配置页 (设置 > 数据安全)

- 策略列表（按数据类型，可编辑脱敏方法和参数）
- 全局/知识库级别切换
- 安全等级阈值配置

### 9.2 文档脱敏报告 (知识库详情 > 文档 > 安全标签)

- 每个文档旁显示安全等级标签 (🟢🟡🟠🔴)
- 点击展开 → 显示检测到的敏感项列表
- 支持人工：确认脱敏 / 标记白名单 / 修改脱敏方式

### 9.3 全局安全仪表盘

- 饼图：各类型敏感信息占比
- 趋势图：每日新增敏感数据量
- 排行榜：含敏感信息最多的文档/知识库

---

## 10. 与 Pipeline 的集成

脱敏系统应作为 Ingestion Pipeline 的**可插拔步骤**：

```yaml
# pipeline_config.yaml
name: "安全文档处理流"
steps:
  - step: "解析"
  - step: "敏感信息扫描"     # ← 脱敏检测
    config:
      detectors: ["PII_PHONE", "PII_IDCARD", "BSI_APIKEY"]
      security_level_threshold: "L2"
  - step: "脱敏执行"          # ← 脱敏替换
    config:
      auto_apply_for: ["L3", "L4"]
      manual_review_for: ["L2"]
  - step: "分块"
  - step: "向量化"
  - step: "质量检查"
```

---

## 11. 合规参考

| 法规 | 要求 | 影响 |
|------|------|------|
| 《个人信息保护法》(PIPL) | 个人信息处理需合法、正当、必要 | PII 必须脱敏或获得授权 |
| 《数据安全法》(DSL) | 数据分级分类管理 | 需要安全等级体系 |
| GDPR (欧盟) | 数据最小化原则 | 仅保留必要信息 |
| HIPAA (美国医疗) | 医疗健康信息保护 | 医疗类知识库需额外保护 |
