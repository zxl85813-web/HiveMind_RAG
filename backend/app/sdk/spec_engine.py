import os
import yaml
import re
from typing import Any, Dict, List
from app.sdk.core import logger

class SpecEntity:
    """代表一个规格实体 (REQ, DES 或 Change)"""
    def __init__(self, entity_id: str, file_path: str, category: str):
        self.id = entity_id
        self.file_path = file_path
        self.category = category  # 'requirement', 'design', 'change'
        self.metadata = {}
        self.references: List[str] = []  # 存储如 REQ-014 等 ID

class SpecEngine:
    """
    改进版全局规格引擎。
    感知并索引全站所有的 Requirement, Design 和 Change 规格。
    """
    def __init__(self, root_dir: str = None):
        if not root_dir:
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        else:
            self.root_dir = root_dir
        
        self.registry: Dict[str, SpecEntity] = {}
        self.patterns = {
            "requirement": re.compile(r"REQ-(\d+)"),
            "design": re.compile(r"DES-(\d+)")
        }

    def scan_all(self):
        """全量扫描全站规格文档"""
        logger.info(f"SpecEngine: Global scan started at {self.root_dir}")
        self.registry.clear()
        
        # 1. 扫描 docs/requirements
        self._scan_dir(os.path.join(self.root_dir, "docs", "requirements"), "requirement")
        
        # 2. 扫描 docs/design
        self._scan_dir(os.path.join(self.root_dir, "docs", "design"), "design")
        
        # 3. 扫描 openspec/changes
        self._scan_changes(os.path.join(self.root_dir, "openspec", "changes"))
        
        # 4. 扫描全局策略文件 (HIVE.md)
        hive_md = os.path.join(self.root_dir, "HIVE.md")
        if os.path.exists(hive_md):
            self.registry["GLOBAL_POLICY"] = SpecEntity("GLOBAL_POLICY", hive_md, "policy")
        
        logger.info(f"SpecEngine: Scan complete. Found {len(self.registry)} specification entities.")

    def _scan_dir(self, path: str, category: str):
        if not os.path.exists(path):
            return
        
        for file in os.listdir(path):
            if file.endswith(".md"):
                # 提取 ID (如 REQ-014)
                for key, pattern in self.patterns.items():
                    if key == category:
                        match = pattern.search(file)
                        if match:
                            entity_id = f"{'REQ' if category == 'requirement' else 'DES'}-{match.group(1)}"
                            entity = SpecEntity(entity_id, os.path.join(path, file), category)
                            entity.references = self._extract_refs(entity.file_path)
                            self.registry[entity_id] = entity

    def _extract_refs(self, file_path: str) -> List[str]:
        """从文件中提取引用的规格 ID"""
        if not os.path.isfile(file_path):
            return []
            
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            # 匹配 REQ-NNN 或 DES-NNN
            refs = re.findall(r"(REQ-\d+|DES-\d+)", content)
            return list(set(refs))

    def _scan_changes(self, path: str):
        if not os.path.exists(path):
            return
        
        for change_id in os.listdir(path):
            change_path = os.path.join(path, change_id)
            if os.path.isdir(change_path):
                entity = SpecEntity(change_id, change_path, "change")
                
                # 特别扫描变更集内部的 tasks.md 或 design.md 以提取引用关系
                for doc_name in ["tasks.md", "design.md"]:
                    doc_path = os.path.join(change_path, doc_name)
                    if os.path.exists(doc_path):
                        entity.references.extend(self._extract_refs(doc_path))
                
                entity.references = list(set(entity.references))
                self.registry[change_id] = entity

    def get_entity(self, entity_id: str) -> SpecEntity | None:
        return self.registry.get(entity_id)

    def generate_report(self) -> Dict[str, Any]:
        """生成全站规格盘点报告"""
        report = {
            "total": len(self.registry),
            "by_category": {
                "requirement": len([e for e in self.registry.values() if e.category == "requirement"]),
                "design": len([e for e in self.registry.values() if e.category == "design"]),
                "change": len([e for e in self.registry.values() if e.category == "change"]),
                "policy": len([e for e in self.registry.values() if e.category == "policy"]),
            },
            "unmapped_changes": [] # TODO: 实现检测未关联 REQ 的 Change
        }
        return report

_spec_engine = None

def get_spec_engine() -> SpecEngine:
    global _spec_engine
    if not _spec_engine:
        _spec_engine = SpecEngine()
        _spec_engine.scan_all()
    return _spec_engine
