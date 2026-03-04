# 🛠️ 后端基础与工具类清单 (Backend Utilities Inventory)

> 所有通用、不属于单一业务范围的工具箱与协议，已在此处枚举。所有开发者在开发新 Service/Router 前请检索，防止重复造轮子。

## 1. 结构与位置

- `app/common/`: 存放业务骨架级的全局规范和基类配置（如返回协议、分页协议、核心 Enum）。
- `app/utils/`: 存放无状态、纯粹被调用的工具辅助函数（如签名计算、随机数生成、深层字典解析）。

---

## 2. 核心共同协议集 `(app/common)`

### 📦 `common.response.ApiResponse`
- **说明**: 规范服务端所有面向外输出的 JSON 结构，内含 `success`, `code`, `message`, `data` 外壳。
- **常用签名**: 
  - `ApiResponse.ok(data: Any, message: str = "Success")`
  - `ApiResponse.error(code: int, message: str, data: Any = None)`
- **什么时候用**: 在每一条 FastAPI 控制器返回时。

### 📦 `common.pagination.Page` & `paginate`
- **说明**: 提供数据库列表分页查询的统一出口模型封装。包含了 `page`, `size`, `total_elements` 等元数据。
- **常用签名**: 
  - `Page[T]` 作为 ResponseModel。
  - `async def paginate(session: AsyncSession, statement, params: PaginationParams)`
- **什么时候用**: API 需要返回超过 50 条数据列表场景（即所有的 `GET /xxx/items` 列表端点）。

### 📦 `common.base.AppException` (或同等基类)
- **说明**: 后端报错处理的基础异常类。
- **什么时候用**: 在 Service 无法找到、无法处理或权限否定需要弹出报错时引发该 Exception，而不要直接向外扔出 `HTTPException`。

---

## 3. 常用工具辅助 `(app/utils/)`

*(当前 utils 目录下暂无大规模通用封装函数。随着开发演进进行记录。)*

**期望未来入库的工具 (Wishlist)**:
- ⏳ `datetime_utils.py` (处理所有时区转换或 ISO8601 标准)
- ⏳ `hash_utils.py` (密码哈希比对与加解密)
- ⏳ `file_parser.py` (获取文件魔数、文件大小计算化单位等)

---

## 4. 提出新的工具封装请求

如果当前库无法满足需求并且你在多个模块拷贝了同样的实现代码：
1. 跑完一个周期的项目 Milestone 开发。
2. 将此痛点通过上报工作流 `workflows/request-component.md` 以 `🔧 UTIL_NEEDED: <你想要的 Util 名字> - <工具函数干啥用>` 标记到 `TODO.md`，交由下一个里程碑重构或专门的 AI Agent 接管实现。
