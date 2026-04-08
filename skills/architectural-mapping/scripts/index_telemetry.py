import os
import xml.etree.ElementTree as ET
import random
from pathlib import Path
from loguru import logger
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")

class TelemetryIndexer:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Connected to Neo4j for Telemetry & APM Mapping")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query, params=None):
        if not self.driver: return []
        with self.driver.session() as session:
            return session.run(query, params or {}).data()

    def index_test_coverage(self):
        """
        Parses coverage.xml if exists, otherwise applies baseline heuristic coverage
        to File nodes to demonstrate Digital Twin capability.
        """
        logger.info("Indexing Code Coverage...")
        cov_file = BASE_DIR / "backend" / "coverage.xml"
        
        file_coverages = {}
        if cov_file.exists():
            try:
                tree = ET.parse(cov_file)
                root = tree.getroot()
                # Parse standard coverage.xml format
                for class_elem in root.iter('class'):
                    filename = class_elem.get('filename')
                    line_rate = float(class_elem.get('line-rate', 0.0))
                    if filename:
                        # Normalize path to match Neo4j
                        normalized_path = f"backend/{filename}".replace("\\", "/")
                        file_coverages[normalized_path] = line_rate
                logger.info(f"Loaded exact coverage data for {len(file_coverages)} files.")
            except Exception as e:
                logger.warning(f"Error parsing coverage.xml: {e}")
        else:
            logger.info("coverage.xml not found. Applying heuristic / simulated coverage mapping for showcase...")
            
        # Update Neo4j nodes
        # First get all files
        files = self.run_query("MATCH (f:File) RETURN f.path AS path")
        updated_count = 0
        for record in files:
            path = record.get("path")
            if not path or "backend" not in path: 
                continue
            
            # Use exact if available, else simulate realistic distributions based on directories
            coverage_rate = file_coverages.get(path)
            if coverage_rate is None:
                if "tests" in path:
                    coverage_rate = 1.0 # purely for demo
                elif "api/routes" in path:
                    coverage_rate = random.uniform(0.6, 0.95)
                elif "services" in path:
                    coverage_rate = random.uniform(0.4, 0.85)
                else:
                    coverage_rate = random.uniform(0.1, 0.7)
            
            self.run_query("""
            MATCH (f:File {path: $path})
            SET f.coverage_rate = $rate,
                f.health_score = CASE WHEN $rate > 0.8 THEN '🟢 GOOD' WHEN $rate > 0.5 THEN '🟡 WARN' ELSE '🔴 POOR' END
            """, {"path": path, "rate": round(coverage_rate, 2)})
            updated_count += 1
            
        logger.success(f"Updated test coverage properties for {updated_count} files.")

    def index_apm_metrics(self):
        """
        Injects Application Performance Monitoring (APM) metrics to APIEndpoint nodes.
        In a real scenario, this fetches from Datadog / Prometheus API.
        """
        logger.info("Generating and Indexing APM Telemetry for API Endpoints...")
        
        # 1. Fetch existing API Endpoints
        endpoints = self.run_query("MATCH (e:APIEndpoint) RETURN e.id AS id")
        
        metrics_injected = 0
        for ep in endpoints:
            ep_id = ep.get("id")
            if not ep_id: continue
            
            # Simulate Telemetry Profile based on HTTP Methods
            method = ep_id.split(":")[0]
            
            # Read-heavy endpoints might have lower errors but higher throughput
            if method == "GET":
                latency_ms = random.randint(15, 300)
                error_rate = round(random.uniform(0.001, 0.02), 4)
                throughput = random.randint(100, 5000)
            else:
                latency_ms = random.randint(100, 1500)
                error_rate = round(random.uniform(0.01, 0.15), 4)
                throughput = random.randint(10, 500)
                
            # Create Metric node and link it
            metric_id = f"METRIC_{ep_id}"
            self.run_query("""
            MATCH (e:APIEndpoint {id: $ep_id})
            MERGE (m:ArchNode:Metric {id: $metric_id})
            SET m.type = 'Metric',
                m.latency_p99_ms = $latency,
                m.error_rate = $err_rate,
                m.tpm = $tpm,
                m.last_updated = datetime()
            MERGE (e)-[:HAS_METRIC]->(m)
            
            // Highlight potential refactor candidates if performance is critical
            SET e.apm_status = CASE 
                WHEN $latency > 1000 OR $err_rate > 0.05 THEN '⚠️ DEGRADED' 
                ELSE '✅ HEALTHY' 
                END
            """, {
                "ep_id": ep_id,
                "metric_id": metric_id,
                "latency": latency_ms,
                "err_rate": error_rate,
                "tpm": throughput
            })
            metrics_injected += 1
            
        logger.success(f"APM metrics injected to {metrics_injected} API endpoints.")

def main():
    load_dotenv(BASE_DIR / "backend" / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    indexer = TelemetryIndexer(uri, user, password)
    indexer.index_test_coverage()
    indexer.index_apm_metrics()
    indexer.close()
    logger.success("Phase 2: Digital Twin Telemetry & APM Mapping Complete!")

if __name__ == "__main__":
    main()
