import sys
import os
sys.path.append(os.getcwd())
try:
    import app.core.embeddings
    print("Import successful")
    print(f"app.core has embeddings: {hasattr(sys.modules['app.core'], 'embeddings')}")
except Exception as e:
    print(f"Import failed: {e}")
