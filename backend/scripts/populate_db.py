import sqlite3
import os

db_path = os.path.join(os.getcwd(), "hivemind.db")
print(f"Opening database at {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get column info
cursor.execute("PRAGMA table_info(swarm_reflections)")
ref_cols = cursor.fetchall()
print("Reflections Columns:")
for col in ref_cols:
    print(f"  - {col[1]} ({col[2]}), notnull: {col[3]}, default: {col[4]}")

cursor.execute("PRAGMA table_info(swarm_todos)")
todo_cols = cursor.fetchall()
print("Todos Columns:")
for col in todo_cols:
    print(f"  - {col[1]} ({col[2]}), notnull: {col[3]}, default: {col[4]}")

# Function to build insert statement with dynamic default values for missing NOT NULL columns
def build_insert_dict(cols, custom_vals):
    insert_dict = {}
    for col in cols:
        name = col[1]
        col_type = col[2].upper()
        notnull = col[3]
        default_val = col[4]
        
        if name in custom_vals:
            insert_dict[name] = custom_vals[name]
        elif notnull:
            if default_val is not None:
                insert_dict[name] = default_val
            else:
                if "INT" in col_type or "REAL" in col_type or "NUM" in col_type:
                    insert_dict[name] = 0
                else:
                    insert_dict[name] = "default"
    return insert_dict

# Clean
try:
    cursor.execute("DELETE FROM swarm_reflections")
    cursor.execute("DELETE FROM swarm_todos")
except Exception as e:
    print("Clean failed:", e)

# Reflections
ref1_vals = {
    'id': 'ref_1', 
    'type': 'self_evaluation', 
    'agent_name': 'code_agent', 
    'summary': 'Completed DeepSeek V4 integration and successfully resolved model name mismatches', 
    'confidence_score': 0.95, 
    'created_at': '2026-05-04 14:59:38',
    'signal_type': 'metric',
    'conversation_id': 'conv_123'
}
ref2_vals = {
    'id': 'ref_2', 
    'type': 'error_correction', 
    'agent_name': 'qa_tester', 
    'summary': 'Found a lint warning in main.py and automatically fixed it', 
    'confidence_score': 0.88, 
    'created_at': '2026-05-04 15:01:22',
    'signal_type': 'metric',
    'conversation_id': 'conv_123'
}

todo1_vals = {
    'id': 'todo_1', 
    'title': 'Implement RAG', 
    'description': 'Build dynamic RAG pipeline', 
    'priority': 'high', 
    'status': 'done', 
    'created_by': 'supervisor', 
    'assigned_to': 'code_agent', 
    'created_at': '2026-05-04 14:55:00'
}

def execute_insert(table_name, cols, vals):
    insert_data = build_insert_dict(cols, vals)
    keys = list(insert_data.keys())
    placeholders = ", ".join([f":{k}" for k in keys])
    col_str = ", ".join(keys)
    query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"
    cursor.execute(query, insert_data)

try:
    execute_insert("swarm_reflections", ref_cols, ref1_vals)
    execute_insert("swarm_reflections", ref_cols, ref2_vals)
    execute_insert("swarm_todos", todo_cols, todo1_vals)
    conn.commit()
    print("Explicitly and dynamically populated hivemind.db successfully!")
except Exception as e:
    print("Insert failed:", e)

conn.close()
