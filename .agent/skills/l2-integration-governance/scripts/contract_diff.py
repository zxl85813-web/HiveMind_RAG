import json
import sys
import argparse
from typing import Dict, Any, List

class ContractDiffAnalyzer:
    """
    OpenAPI Breaking Change Analyzer.
    Ensures downward compatibility between Provider and Consumer.
    """
    
    def __init__(self):
        self.breaking_changes = []

    def load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            sys.exit(1)

    def analyze(self, baseline: Dict[str, Any], current: Dict[str, Any]):
        """Compares two OpenAPI definitions."""
        self.breaking_changes = []
        
        # 1. Check for removed paths
        b_paths = baseline.get("paths", {})
        c_paths = current.get("paths", {})
        
        for path, methods in b_paths.items():
            if path not in c_paths:
                self.breaking_changes.append(f"❌ REMOVED PATH: {path}")
                continue
            
            # 2. Check for removed methods on path
            for method in methods:
                if method not in c_paths[path]:
                    self.breaking_changes.append(f"❌ REMOVED METHOD: {method.upper()} on {path}")

        # 3. Check for deleted fields in Shared Components (Schemas)
        b_schemas = baseline.get("components", {}).get("schemas", {})
        c_schemas = current.get("components", {}).get("schemas", {})
        
        for schema_name, schema_body in b_schemas.items():
            if schema_name not in c_schemas:
                self.breaking_changes.append(f"❌ REMOVED SCHEMA: {schema_name}")
                continue
                
            b_props = schema_body.get("properties", {})
            c_props = c_schemas[schema_name].get("properties", {})
            
            for prop in b_props:
                if prop not in c_props:
                    self.breaking_changes.append(f"❌ REMOVED PROPERTY: '{prop}' in Schema '{schema_name}'")
                else:
                    # 4. Check for type mismatch
                    b_type = b_props[prop].get("type")
                    c_type = c_props[prop].get("type")
                    if b_type != c_type:
                        self.breaking_changes.append(f"⚠️ TYPE DRIFT: Property '{prop}' in '{schema_name}' changed from {b_type} to {c_type}")

        return self.breaking_changes

    def print_report(self):
        print("\n--- [CONTRACT BREAKING CHANGE REPORT] ---")
        if not self.breaking_changes:
            print("✅ No Breaking Changes detected. Contract is safe.")
        else:
            for change in self.breaking_changes:
                print(change)
            print(f"\n🚨 FAILURE: Total {len(self.breaking_changes)} breaking changes found. Pull Request should be BLOCKED.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", help="Path to baseline openapi.json", required=True)
    parser.add_argument("--current", help="Path to current openapi.json", required=True)
    args = parser.parse_args()
    
    analyzer = ContractDiffAnalyzer()
    b_json = analyzer.load_json(args.baseline)
    c_json = analyzer.load_json(args.current)
    
    changes = analyzer.analyze(b_json, c_json)
    analyzer.print_report()
    
    sys.exit(1 if changes else 0)
