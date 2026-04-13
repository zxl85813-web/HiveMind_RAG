#!/bin/bash

# 🛡️ [FE-GOV-SYNC]: API 类型同步脚本
# 运行此脚本以确保前端类型与后端 Pydantic 模型严格对齐。

set -e

# 定位路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
FRONTEND_DIR="$( dirname "$SCRIPT_DIR" )"
PROJECT_ROOT="$( dirname "$FRONTEND_DIR" )"
OPENAPI_JSON="$PROJECT_ROOT/docs/api/openapi.json"
OUTPUT_FILE="$FRONTEND_DIR/src/types/api.generated.ts"

# 1. 确保后端生成了最新的 JSON
echo "🏗️ Step 1: Exporting OpenAPI from Backend..."
cd "$PROJECT_ROOT/backend"
python scripts/export_openapi.py

# 2. 检查 openapi-typescript 是否安装
cd "$FRONTEND_DIR"
if ! npx openapi-typescript --version > /dev/null 2>&1; then
    echo "📦 Installing openapi-typescript..."
    npm install -D openapi-typescript
fi

# 3. 生成类型
echo "🧬 Step 2: Generating TypeScript types from OpenAPI..."
npx openapi-typescript "$OPENAPI_JSON" --output "$OUTPUT_FILE"

echo "✅ Success! API types are now synced at: $OUTPUT_FILE"
echo "👉 Use them in your code: import type { components } from '../types/api.generated';"
