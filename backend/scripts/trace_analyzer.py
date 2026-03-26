"""
🕵️ Trace Analyzer — HiveMind 系统链路可视化分析工具
═════════════════════════════════════════════════════════════

用法: python scripts/trace_analyzer.py --id <trace_id>

功能:
1. 在 logs/ 目录下递归扫描所有结构化日志。
2. 聚合指定 trace_id 的所有碎片。
3. 按照时间戳重建“意识流”链路。
4. 自动区分 前端 (FE) 和 后端 (BE) 的行为。
"""

import os
import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("trace_analyzer")
t_logger = get_trace_logger("scripts.trace_analyzer")


# --- 控制台颜色控制 ---
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def analyze_trace(trace_id: str, log_dir: str = "logs"):
    t_logger.info(f"Analyzing Agent Trace Chain: {trace_id}", action="analysis_start", meta={"trace_id": trace_id})
    print(f"\n{Color.BOLD}🕵️ [HiveMind] Analyzing Agent Trace Chain: {trace_id}{Color.END}")
    print("═" * 80)
    
    # ... (原有逻辑)
    all_logs = []
    log_path = Path(log_dir)

    if not log_path.exists():
        t_logger.error(f"Log directory not found: {log_dir}")
        print(f"❌ Log directory not found: {log_dir}")
        return

    # 1. 扫描所有日志文件
    for log_file in log_path.glob("*.log"):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    record = data.get("record", {})
                    extra = record.get("extra", {})
                    
                    # 匹配 Trace ID (直接匹配或嵌套在 JSON 消息中)
                    target_tid = extra.get("trace_id")
                    
                    if target_tid == trace_id:
                        all_logs.append({
                            "ts": record.get("time", {}).get("timestamp", 0) or 0,
                            "level": record.get("level", {}).get("name", "INFO"),
                            "module": extra.get("module", "unknown"),
                            "platform": extra.get("platform", "BE"),
                            "msg": record.get("message", ""),
                            "extra": extra
                        })
                except Exception:
                    continue

    if not all_logs:
        t_logger.warning(f"No logs found for Trace ID: {trace_id}", action="analysis_empty")
        print(f"📭 No logs found for Trace ID: {Color.RED}{trace_id}{Color.END}")
        return

    # 2. 排序 (按时间戳)
    all_logs.sort(key=lambda x: x["ts"])

    # 3. 可视化输出
    for log in all_logs:
        ts_str = datetime.fromtimestamp(log["ts"]).strftime("%H:%M:%S.%f")[:-3]
        
        # 平台图标
        platform_icon = "💻 [FE]" if log["platform"] == "FE" else "🐝 [BE]"
        platform_color = Color.CYAN if log["platform"] == "FE" else Color.YELLOW
        
        # 级别颜色
        level_color = Color.GREEN
        if log["level"] == "ERROR": level_color = Color.RED
        if log["level"] == "WARNING": level_color = Color.YELLOW

        # 模块标识
        module_tag = f"<{log['module']}>"
        
        print(f"[{Color.DARKCYAN}{ts_str}{Color.END}] {platform_color}{platform_icon}{Color.END} {level_color}{log['level']:<7}{Color.END} {Color.BOLD}{module_tag:18}{Color.END} | {log['msg']}")
        
        # 重点提取 Meta 数据中的关键动作
        meta = log["extra"]
        if "action" in meta:
            print(f"    └─ {Color.BLUE}Action:{Color.END} {meta['action']}")
        
        # 如果是前端报错，打印 Stack 摘要
        if log["platform"] == "FE" and "error" in log["msg"].lower():
             print(f"    └─ {Color.RED}Detected Error Event in Frontend.{Color.END}")

    print("═" * 80)
    t_logger.success(f"Analysis complete. Total {len(all_logs)} chain fragments found.", action="analysis_complete")
    print(f"{Color.GREEN}✅ [Summary] Analysis complete. Total {len(all_logs)} chain fragments found.{Color.END}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze HiveMind traces from JSON logs.")
    parser.add_argument("--id", required=True, help="The Trace ID to search for.")
    parser.add_argument("--dir", default="logs", help="The log directory (default: logs).")

    args = parser.parse_args()
    analyze_trace(args.id, args.dir)
