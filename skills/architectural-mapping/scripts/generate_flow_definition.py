"""
Flow Definition Generator — 从 Neo4j 图谱自动生成业务流程 YAML。

用法:
    python generate_flow_definition.py --module knowledge --output docs/flows/FLOW-001-knowledge-lifecycle.yaml
    python generate_flow_definition.py --module evaluation
    python generate_flow_definition.py --module chat

原理:
    1. 从图谱查询指定模块的所有 API 端点（按 CRUD 顺序排列）
    2. 查询每个端点的 Request/Response Schema + 字段
    3. 查询每个端点操作的 DB 表 + 该表的状态机转换
    4. 查询每个端点的权限守卫
    5. 查询相关的事件发布
    6. 组装成 YAML 格式输出

人需要 review 的部分（会用 # TODO: REVIEW 标记）:
    - 步骤顺序（AI 按 CRUD 排，但实际业务可能不同）
    - 断言的具体值（AI 能推断初始状态，但不知道具体业务预期）
    - 前置条件的描述
    - 错误路径的触发条件
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from loguru import logger

# Load env
BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / "backend" / ".env")


def get_driver():
    from neo4j import GraphDatabase
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD", "")
    return GraphDatabase.driver(uri, auth=(user, pwd))


def query(session, cypher, params=None):
    return session.run(cypher, params or {}).data()


def generate_flow(module: str, flow_id: str = None, flow_name: str = None) -> dict:
    """Generate a complete flow definition from graph data."""
    driver = get_driver()

    with driver.session() as s:
        # 1. Get all API endpoints for this module, ordered by CRUD convention
        endpoints = query(s, """
            MATCH (ep:APIEndpoint)
            WHERE ep.module = $module AND ep.method IS NOT NULL
            OPTIONAL MATCH (ep)-[:OPERATES_ON]->(t:DBTable)
            OPTIONAL MATCH (ep)-[:GUARDED_BY]->(g:GateRule)
            OPTIONAL MATCH (ep)-[:REQUEST_SCHEMA]->(req:APISchema)
            OPTIONAL MATCH (ep)-[:RESPONSE_SCHEMA]->(resp:APISchema)
            RETURN ep.method AS method, ep.path AS path, ep.handler AS handler,
                   collect(DISTINCT t.table_name) AS tables,
                   collect(DISTINCT g.value) AS permissions,
                   req.name AS request_schema,
                   resp.name AS response_schema
            ORDER BY
                CASE ep.method
                    WHEN 'POST' THEN 1
                    WHEN 'GET' THEN 2
                    WHEN 'PUT' THEN 3
                    WHEN 'DELETE' THEN 4
                    ELSE 5
                END,
                ep.path
        """, {"module": module})

        if not endpoints:
            logger.warning(f"No endpoints found for module '{module}'")
            driver.close()
            return {}

        # 2. Get schema fields for each referenced schema
        schema_cache = {}
        for ep in endpoints:
            for schema_name in [ep.get("request_schema"), ep.get("response_schema")]:
                if schema_name and schema_name not in schema_cache:
                    fields = query(s, """
                        MATCH (sc:APISchema {name: $name})-[:HAS_FIELD]->(f:SchemaField)
                        RETURN f.name AS name, f.field_type AS type, f.is_optional AS optional
                        ORDER BY f.is_optional, f.name
                    """, {"name": schema_name})
                    schema_cache[schema_name] = fields

        # 3. Get state machines for tables involved
        table_names = set()
        for ep in endpoints:
            table_names.update(ep.get("tables", []))

        state_machines = {}
        for table in table_names:
            if not table:
                continue
            sm_data = query(s, """
                MATCH (t:DBTable {table_name: $table})-[:HAS_STATE_MACHINE]->(sm:StateMachine)
                MATCH (sm)-[:HAS_STATE]->(st:EntityState)
                OPTIONAL MATCH (st)-[tr:TRANSITIONS_TO]->(next:EntityState)
                RETURN sm.entity AS entity, sm.field AS field,
                       st.value AS from_state, st.is_initial AS is_initial,
                       tr.trigger AS trigger, next.value AS to_state
                ORDER BY st.is_initial DESC, st.value
            """, {"table": table})
            if sm_data:
                state_machines[table] = sm_data

        # 4. Get related events
        events_data = query(s, """
            MATCH (f:File)-[:PUBLISHES_TO]->(ch:EventChannel)-[:CARRIES]->(evt:EventType)
            WHERE f.id CONTAINS $module
            RETURN DISTINCT ch.name AS channel, evt.name AS event_type
        """, {"module": module})

        # 5. Get page info
        page_data = query(s, """
            MATCH (pg:Page) WHERE pg.key = $module
            RETURN pg.path AS path, pg.category AS category, pg.is_protected AS is_protected
        """, {"module": module})

    driver.close()

    # === Assemble YAML ===
    if not flow_id:
        flow_id = f"FLOW-{module.upper()}-001"
    if not flow_name:
        flow_name = f"{module.title()} 业务流程"

    page_path = page_data[0]["path"] if page_data else f"/{module}"

    steps = []
    seq = 1

    # Group endpoints: POST first (create), then GET (read), PUT (update), DELETE
    method_order = {"POST": 1, "GET": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}
    sorted_eps = sorted(endpoints, key=lambda e: (method_order.get(e["method"], 9), e["path"]))

    # Filter to write operations for main flow steps, keep GETs as verification steps
    write_eps = [e for e in sorted_eps if e["method"] in ("POST", "PUT", "PATCH", "DELETE")]
    read_eps = [e for e in sorted_eps if e["method"] == "GET"]

    for ep in write_eps:
        step = {
            "seq": seq,
            "name": f"# TODO: REVIEW - 给这个步骤一个业务名称\n{ep['method']} {ep['path']}",
            "page": page_path,
            "api": f"{ep['method']} {ep['path']}",
            "handler": ep["handler"],
        }

        # Request schema
        if ep.get("request_schema") and ep["request_schema"] in schema_cache:
            fields = schema_cache[ep["request_schema"]]
            req = {}
            for f in fields:
                if f["optional"]:
                    req[f["name"]] = f"# optional ({f['type']})"
                else:
                    # Generate example values based on type
                    example = _example_value(f["name"], f["type"])
                    req[f["name"]] = example
            step["request"] = req
            step["request_schema"] = ep["request_schema"]

        # Response expectations
        step["response"] = {
            "status_code": 200,
            "# TODO: REVIEW": "补充具体的响应断言",
        }
        if ep.get("response_schema") and ep["response_schema"] in schema_cache:
            resp_fields = schema_cache[ep["response_schema"]]
            step["response"]["schema"] = ep["response_schema"]
            step["response"]["key_fields"] = [f["name"] for f in resp_fields if not f["optional"]][:5]

        # DB writes
        if ep.get("tables"):
            db_writes = []
            for table in ep["tables"]:
                if not table:
                    continue
                write = {"table": table}
                if table in state_machines:
                    # Find initial state
                    initial = next((sm for sm in state_machines[table] if sm.get("is_initial")), None)
                    if initial:
                        write["initial_status"] = initial["from_state"]
                        write["status_field"] = state_machines[table][0].get("field", "status")
                db_writes.append(write)
            if db_writes:
                step["db_writes"] = db_writes

        # State transitions
        for table in (ep.get("tables") or []):
            if table in state_machines:
                transitions = []
                for sm in state_machines[table]:
                    if sm.get("trigger") and sm.get("to_state"):
                        transitions.append({
                            "entity": sm["entity"],
                            "from": sm["from_state"],
                            "to": sm["to_state"],
                            "trigger": sm["trigger"],
                        })
                if transitions:
                    step["state_transitions"] = transitions[:5]  # Limit

        # Permissions
        if ep.get("permissions"):
            step["permissions"] = ep["permissions"]

        # Precondition
        if seq == 1:
            step["precondition"] = "用户已登录"
        else:
            step["precondition"] = f"# TODO: REVIEW - step {seq-1} 完成后的前置条件"

        steps.append(step)
        seq += 1

    # Add a verification step using GET endpoints
    if read_eps:
        verify_step = {
            "seq": seq,
            "name": "# TODO: REVIEW - 验证步骤",
            "type": "verification",
            "apis": [f"GET {e['path']}" for e in read_eps[:3]],
            "assert": "# TODO: REVIEW - 补充验证断言（如：列表中应包含新创建的资源）",
        }
        steps.append(verify_step)

    # Error paths
    error_paths = []
    for ep in write_eps[:3]:
        # Permission denied
        if ep.get("permissions"):
            error_paths.append({
                "name": f"权限不足 - {ep['handler']}",
                "at_step": "# TODO: REVIEW",
                "trigger": f"用户无 {ep['permissions'][0]} 权限",
                "expected": "403 Forbidden",
            })

        # For endpoints with state machines, add invalid state transition
        for table in (ep.get("tables") or []):
            if table in state_machines:
                terminals = [sm for sm in state_machines[table]
                             if sm.get("from_state") and not sm.get("to_state")]
                for t in terminals[:1]:
                    error_paths.append({
                        "name": f"非法状态操作 - {t['from_state']}",
                        "at_step": "# TODO: REVIEW",
                        "trigger": f"实体处于终态 {t['from_state']}，不应允许此操作",
                        "expected": "400 Bad Request 或业务逻辑拒绝",
                    })

    # Events
    events = []
    for evt in events_data:
        events.append({
            "channel": evt["channel"],
            "event_type": evt["event_type"],
            "triggered_at": "# TODO: REVIEW - 在哪个步骤触发",
        })

    # Final assembly
    flow = {
        "id": flow_id,
        "name": flow_name,
        "description": f"# TODO: REVIEW - 补充业务描述",
        "module": module,
        "page": page_path,
        "generated_from": "Neo4j Knowledge Graph (auto-generated)",
        "review_status": "PENDING_REVIEW",
        "steps": steps,
    }

    if error_paths:
        flow["error_paths"] = error_paths
    if events:
        flow["events"] = events

    return flow


def _example_value(field_name: str, field_type: str) -> str:
    """Generate example values based on field name and type."""
    name_lower = field_name.lower()
    type_lower = field_type.lower()

    if "name" in name_lower:
        return "测试名称"
    if "description" in name_lower or "desc" in name_lower:
        return "测试描述"
    if "email" in name_lower:
        return "test@example.com"
    if "password" in name_lower:
        return "test_password_123"
    if "url" in name_lower or "path" in name_lower:
        return "https://example.com"
    if "id" in name_lower:
        return "{dynamic_id}"
    if "boolean" in type_lower:
        return "false"
    if "number" in type_lower or "int" in type_lower or "float" in type_lower:
        return "0"
    if "string" in type_lower:
        return "test_value"
    return f"# TODO: fill ({field_type})"


def main():
    parser = argparse.ArgumentParser(description="Generate business flow YAML from Neo4j graph")
    parser.add_argument("--module", required=True, help="API module name (e.g. knowledge, evaluation, chat)")
    parser.add_argument("--flow-id", default=None, help="Flow ID (e.g. FLOW-001)")
    parser.add_argument("--flow-name", default=None, help="Flow name")
    parser.add_argument("--output", default=None, help="Output YAML file path")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of file")
    args = parser.parse_args()

    flow = generate_flow(args.module, args.flow_id, args.flow_name)
    if not flow:
        print("No data generated.")
        return

    yaml_str = yaml.dump(flow, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)

    if args.stdout:
        print(yaml_str)
    else:
        output_path = args.output or f"docs/flows/FLOW-{args.module.upper()}-001.yaml"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Auto-generated from Neo4j Knowledge Graph\n")
            f.write(f"# Review items marked with '# TODO: REVIEW'\n")
            f.write(f"# After review, change review_status to 'APPROVED'\n\n")
            f.write(yaml_str)
        print(f"✅ Generated: {output_path}")
        # Count TODOs
        todo_count = yaml_str.count("# TODO: REVIEW")
        print(f"📋 {todo_count} items need human review (search for '# TODO: REVIEW')")


if __name__ == "__main__":
    main()
