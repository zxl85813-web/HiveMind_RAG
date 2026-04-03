# Architectural Governance & Cross-View Verification

This skill is designed to prevent architectural erosion (fragmentation) caused by AI-generated "isolated" code. It leverages Tree-sitter AST fingerprints and Neo4j knowledge graphs to enforce code reuse and structural integrity.

## Core Perspectives

### 1. Pattern Reuse (The Finder)
**Goal:** Prevent reinventing the wheel.
- Before implementing any new Hook, Service, or Component, run the `code_similarity_tool.py` on a "mock" or "planned" structure.
- Query Neo4j for nodes with similar tags or descriptions.
- **Rule:** If similarity > 80% with an existing entity, the implementation MUST be a refactor or a wrapper, not a new file.

### 2. Structural Compliance (The Guard)
**Goal:** Enforce layering rules.
- Check the AST of the proposed change using `index_architecture.py`.
- **Rule:** Frontend code MUST NOT import from `backend/app/models`.
- **Rule:** API calls MUST use the defined `services/` layer, not raw `axios` or `fetch` calls in components.

### 3. Traceability Alignment (The Validator)
**Goal:** Ensure every line of code has a "Reason for Being".
- Verify that the new code is linked to a `REQ-XXX` and a `DES-XXX` in the Neo4j graph.
- **Rule:** Orphaned files (unconnected in the graph) are rejected.

## Tools Integrated
- `code_similarity_tool.py`: For structural fingerprint matching.
- `index_architecture.py`: For graph registration and dependency analysis.
- `neo4j`: As the source of truth for traceability.

## Review Protocol (Cross-View)
When reviewing a Pull Request or a code change:
1. **Structural Review:** Does the AST look clean and modular?
2. **Similarity Review:** Is this code too similar to another file? (Threshold: 90%)
3. **Traceability Review:** Is there an updated Design Doc and Requirement link?

Pass all three to achieve **ARCH-ROBUST** status.
