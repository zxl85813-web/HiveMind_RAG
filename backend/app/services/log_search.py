import os
import json
from pathlib import Path
from typing import List, Dict, Any
from app.sdk.core.logging import logger

class LogSearchService:
    @staticmethod
    async def search_logs(query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        [M8.2] 日志语义检索辅助服务。
        支持 AI Agent 快速检索全栈逻辑（FE+BE），辅助排障。
        """
        log_dir = Path("logs")
        if not log_dir.exists():
            return []

        results = []
        # 搜索最近的日志文件
        log_files = sorted(list(log_dir.glob("hivemind_*.log")), reverse=True)
        
        for log_file in log_files:
            if len(results) >= limit:
                break
                
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    # 日志是序列化的 JSON (one per line)
                    lines = f.readlines()
                    # 倒序搜索最新日志
                    for line in reversed(lines):
                        if query.lower() in line.lower():
                            try:
                                entry = json.loads(line)
                                results.append(entry)
                            except:
                                # 非 JSON 格式 fallback
                                results.append({"raw": line})
                                
                        if len(results) >= limit:
                            break
            except Exception as e:
                logger.error(f"Failed to read log file {log_file}: {e}")

        return results

log_search_service = LogSearchService()
