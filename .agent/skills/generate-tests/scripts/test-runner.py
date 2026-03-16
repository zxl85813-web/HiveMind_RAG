import subprocess
import sys
import os

def run_test(file_path: str):
    print(f"🚀 Running tests in: {file_path}")
    
    # Ensure we are in the project root if needed, or adjust paths
    cmd = ["pytest", "-v", file_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ All tests passed!")
            print(result.stdout)
            sys.exit(0)
        else:
            print("❌ Some tests failed.")
            print(result.stdout)
            print(result.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: 'pytest' command not found. Please install it.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test-runner.py <path_to_test_file>")
        sys.exit(1)
    run_test(sys.argv[1])
