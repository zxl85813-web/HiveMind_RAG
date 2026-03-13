Thinking: Requirement REQ-011 is about Changelog RAG. 
Instead of searching everywhere, I will query the architectural knowledge graph to find precisely which designs and files are related.

Command: python skills/architectural-mapping/scripts/query_architecture.py --req "REQ-011"

Result Output (Mocked): 
[
  {"req": "REQ-011", "designs": ["DES-011"], "files": ["backend/app/services/retrieval/steps.py"], "skills": []}
]

Action: I will now only read 'backend/app/services/retrieval/steps.py'.
Tokens Saved: High (Avoiding reading entire backend directory).
