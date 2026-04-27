import os
import json
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from app.sdk.core.graph_store import get_graph_store

class GraphEvolutionService:
    """
    Service for evolving the architectural graph with dynamic metadata.
    @covers REQ-027
    """

    def __init__(self):
        self.graph_store = get_graph_store()
        self.root_dir = Path(r"c:\Users\linkage\Desktop\aiproject")

    async def scan_supply_chain(self) -> Dict[str, Any]:
        """
        [Phase 1] SBOM Scan: Identify and map third-party dependencies.
        """
        results = {
            "backend_packages": [],
            "frontend_packages": [],
            "links_created": 0
        }

        # 1. Backend: Scan pyproject.toml
        toml_file = self.root_dir / "backend" / "pyproject.toml"
        if toml_file.exists():
            logger.info("Scanning backend pyproject.toml...")
            import tomllib
            try:
                with open(toml_file, "rb") as f:
                    data = tomllib.load(f)
                    # Main dependencies
                    deps = data.get("project", {}).get("dependencies", [])
                    # Dev dependencies
                    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
                    
                    for dep in deps + dev_deps:
                        # Simple split for version constraints: name>=1.0.0 or name
                        name = dep.split(">=")[0].split("==")[0].split("[")[0].strip()
                        results["backend_packages"].append({"name": name, "version": "constrained"})
                        await self._upsert_package(name, "constrained", "backend")
            except Exception as e:
                logger.error(f"Failed to parse backend pyproject.toml: {e}")

        # 2. Frontend: Scan package.json
        pkg_json = self.root_dir / "frontend" / "package.json"
        if pkg_json.exists():
            logger.info("Scanning frontend dependencies...")
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    for name, version in deps.items():
                        results["frontend_packages"].append({"name": name, "version": version})
                        await self._upsert_package(name, version, "frontend")
            except Exception as e:
                logger.error(f"Failed to parse frontend package.json: {e}")

        logger.info(f"Supply chain scan complete. Found {len(results['backend_packages'])} backend and {len(results['frontend_packages'])} frontend packages.")
        return results

    async def _upsert_package(self, name: str, version: str, ecosystem: str):
        """
        Create or update a Package node and link it to the project root.
        """
        query = """
        MERGE (p:Package {name: $name, ecosystem: $ecosystem})
        SET p.version = $version, p.updated_at = timestamp()
        WITH p
        MATCH (pr:Project)
        MERGE (pr)-[:DEPENDS_ON]->(p)
        RETURN count(p) as count
        """
        await self.graph_store.execute_query(query, {"name": name, "version": version, "ecosystem": ecosystem})

    async def inject_coverage_metrics(self, cov_report_path: str):
        """
        [Phase 2] Coverage Injection: Enrich File nodes with test coverage data from Cobertura XML.
        """
        import xml.etree.ElementTree as ET
        
        if not os.path.exists(cov_report_path):
             logger.error(f"Coverage file not found: {cov_report_path}")
             return

        logger.info(f"Parsing coverage report: {cov_report_path}")
        try:
            tree = ET.parse(cov_report_path)
            root = tree.getroot()
            
            file_metrics = []
            # Find all <class> elements which represent files
            for cls in root.findall(".//class"):
                file_path = cls.get("filename")
                line_rate = float(cls.get("line-rate", 0))
                # Normalize path if needed (though Cobertura usually uses relative to root)
                file_metrics.append({"path": file_path, "coverage": line_rate})
                
            if not file_metrics:
                logger.warning("No file metrics found in coverage report.")
                return

            logger.info(f"Injecting coverage for {len(file_metrics)} files...")
            query = """
            UNWIND $files as file_info
            MATCH (f:File {path: file_info.path})
            SET f.coverage = file_info.coverage, f.indexed_at = timestamp()
            RETURN count(f) as count
            """
            result = await self.graph_store.execute_query(query, {"files": file_metrics})
            logger.info(f"Coverage injection complete. Injected metrics for {len(file_metrics)} potential files.")
        except Exception as e:
            logger.error(f"Failed to parse or inject coverage: {e}")

    async def audit_pii_surface(self):
        """
        [Phase 3] SME Audit: Automatically identify and tag PII-sensitive files.
        """
        PII_KEYWORDS = {"email", "phone", "password", "secret", "token", "address", "birthday", "credit_card", "balance"}
        logger.info("Starting PII surface audit...")
        
        pii_results = []
        
        # Scan models and schemas
        model_dirs = [
            self.root_dir / "backend" / "app" / "models",
            self.root_dir / "backend" / "app" / "schemas"
        ]
        
        for mdir in model_dirs:
            if not mdir.exists(): continue
            for py_file in mdir.glob("**/*.py"):
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        found_keywords = [k for k in PII_KEYWORDS if k in content]
                        if found_keywords:
                            # Convert absolute to relative path
                            rel_path = os.path.relpath(py_file, self.root_dir).replace("\\", "/")
                            pii_results.append({
                                "path": rel_path,
                                "keywords": found_keywords
                            })
                except Exception as e:
                    logger.warning(f"Failed to scan {py_file} for PII: {e}")

        if not pii_results:
            logger.info("No PII-sensitive files detected.")
            return

        logger.info(f"Tagging {len(pii_results)} files as PII-sensitive...")
        query = """
        UNWIND $files as item
        MATCH (f:File {path: item.path})
        SET f.is_pii = true, f.pii_keywords = item.keywords, f.indexed_at = timestamp()
        RETURN count(f) as count
        """
        result = await self.graph_store.execute_query(query, {"files": pii_results})
        logger.info(f"PII Audit complete. Tagged {result} files.")
        return pii_results

# Singleton instance
evolution_service = GraphEvolutionService()
