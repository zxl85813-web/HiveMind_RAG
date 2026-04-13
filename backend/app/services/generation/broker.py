from typing import Any, Dict, Tuple, Optional
from app.core.logging import get_trace_logger

# 获取追踪日志记录器
logger = get_trace_logger(__name__)

class ContextBroker:
    """
    统一上下文经纪人 (Phase 2 - VFS 架构)。
    
    该组件支持层次化的路径隔离（采用 viking:// 协议），模拟了一个专门供智体（Agent）
    使用的作用域文件系统。它解决了多智体协作中“谁拥有什么上下文”以及“上下文如何跨节点传递”的问题。
    
    层级结构示例：
    - global: 全局配置与公共知识
    - sessions: 特定会话的中间过程数据
    - agents: 智体私有的状态空间
    """
    def __init__(self):
        # 内部树形存储结构
        self._tree: Dict[str, Any] = {
            "global": {},
            "sessions": {},
            "agents": {}
        }
    
    def _parse_path(self, path: str, create: bool = False) -> Optional[Tuple[Dict[str, Any], str]]:
        """
        解析 viking:// 协议路径并导航树结构。
        
        示例路径: viking://sessions/task-123/shared/docs
        
        参数:
            path: 虚拟路径字符串
            create: 如果中间路径不存在，是否自动创建目录节点
        
        返回:
            元组 (父节点字典, 目标键名) 或 None
        """
        # 协议清洗与路径对齐
        clean_path = path.replace("viking://", "").strip("/")
        parts = clean_path.split("/")
        
        curr = self._tree
        # 深度垂直搜索，导航至目标父节点
        for p in parts[:-1]:
            if p not in curr:
                if create:
                    curr[p] = {}
                else:
                    return None
            curr = curr[p]
        
        return curr, parts[-1]
    
    def page_out(self, path: str, payload: Any):
        """
        写入数据到指定的 VFS 路径 (Page-Out)。
        相当于文件系统的 'write' 操作。
        """
        res = self._parse_path(path, create=True)
        if res:
            node, key = res
            logger.debug(f"VFS 写入 -> {path} (类型: {type(payload).__name__})")
            node[key] = payload
        
    def page_in(self, path: str, default: Any = None) -> Any:
        """
        从指定的 VFS 路径读取数据 (Page-In)。
        相当于文件系统的 'read' 操作。
        """
        res = self._parse_path(path)
        if res:
            node, key = res
            val = node.get(key, default)
            logger.debug(f"VFS 读取 <- {path} (命中: {val is not default})")
            return val
        return default
        
    def clear(self, path: str):
        """
        销毁 VFS 树中的节点或叶子。
        用于清理会话结束后的瞬时上下文，防止内存溢出。
        """
        res = self._parse_path(path)
        if res:
            node, key = res
            if key in node:
                logger.debug(f"VFS 清理 -- {path}")
                del node[key]

    def list_dir(self, path: str) -> list[str]:
        """
        列出指定 VFS 路径下的所有键（类似于 'ls' 命令）。
        用于智体发现当前作用域内可用的上下文资产。
        """
        clean_path = path.replace("viking://", "").strip("/")
        parts = [p for p in clean_path.split("/") if p]
        
        curr = self._tree
        for p in parts:
            if not isinstance(curr, dict) or p not in curr:
                return []
            curr = curr[p]
            
        return list(curr.keys()) if isinstance(curr, dict) else []

# 全局唯一经纪人实例
broker = ContextBroker()
