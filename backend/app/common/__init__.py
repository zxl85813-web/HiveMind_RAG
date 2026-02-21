"""
通用基础组件 — 跨模块共享的类型、Mixin、工具。

提供:
    - base.py       — Model 基类 Mixin (时间戳/软删除/ID)
    - enums.py      — 通用枚举 (状态/优先级)
    - pagination.py — 统一分页
    - response.py   — 统一 API 响应包装

定位:
    core/   = 框架级基础设施 (config/db/logging)，不含业务
    common/ = 跨业务模块共享的类型和工具
    utils/  = 纯函数工具 (无状态、无依赖)

参见: REGISTRY.md > 后端 > common 模块
"""
