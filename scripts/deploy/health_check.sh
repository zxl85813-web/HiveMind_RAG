#!/usr/bin/env bash
# =============================================================================
# HiveMind RAG — Post-Deployment Health Check & Smoke Test Suite
# =============================================================================
# 用途：部署完成后的全面健康验证，可被 Harness CD 或 GitHub Actions 调用
#
# 退出码:
#   0 — 所有检查通过
#   1 — 一个或多个检查失败
#
# 使用方式:
#   ./health_check.sh                        # 检查当前活跃 slot
#   ./health_check.sh --slot blue            # 检查指定 slot
#   ./health_check.sh --full                 # 包含 LLM 路由冒烟测试（需要真实 API Key）
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[CHECK]${NC} $*"; }
log_pass()    { echo -e "${GREEN}[PASS]${NC}  $*"; }
log_fail()    { echo -e "${RED}[FAIL]${NC}  $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }

PROJECT_DIR="${PROJECT_DIR:-/home/azureuser/HiveMind_RAG}"
STATE_FILE="${PROJECT_DIR}/.deploy_state"
FULL_CHECK=false
TARGET_SLOT=""
FAILURES=0

while [[ $# -gt 0 ]]; do
  case $1 in
    --slot)  TARGET_SLOT="$2"; shift 2 ;;
    --full)  FULL_CHECK=true; shift ;;
    *)       shift ;;
  esac
done

# 确定检查的 slot 和端口
if [[ -z "$TARGET_SLOT" ]]; then
  [[ -f "$STATE_FILE" ]] && TARGET_SLOT=$(cat "$STATE_FILE") || TARGET_SLOT="blue"
fi
[[ "$TARGET_SLOT" == "blue" ]] && BACKEND_PORT=8000 || BACKEND_PORT=8001
FRONTEND_PORT=80
BASE_URL="http://localhost:${BACKEND_PORT}/api/v1"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HiveMind RAG — Health Check Suite"
echo "  Slot: ${TARGET_SLOT} | Backend: :${BACKEND_PORT} | Frontend: :${FRONTEND_PORT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 辅助函数 ──────────────────────────────────────────────────────────────────
check_http() {
  local name="$1"
  local url="$2"
  local expected_code="${3:-200}"

  local actual_code
  actual_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" || echo "000")

  if [[ "$actual_code" == "$expected_code" ]]; then
    log_pass "${name} → HTTP ${actual_code}"
  else
    log_fail "${name} → Expected HTTP ${expected_code}, got ${actual_code} (URL: ${url})"
    FAILURES=$(( FAILURES + 1 ))
  fi
}

check_container() {
  local name="$1"
  local container="$2"

  local status
  status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")
  local health
  health=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no_healthcheck")

  if [[ "$status" == "running" ]]; then
    if [[ "$health" == "healthy" || "$health" == "no_healthcheck" ]]; then
      log_pass "${name} → running (health: ${health})"
    else
      log_fail "${name} → running but health=${health}"
      FAILURES=$(( FAILURES + 1 ))
    fi
  else
    log_fail "${name} → status=${status}"
    FAILURES=$(( FAILURES + 1 ))
  fi
}

check_json_field() {
  local name="$1"
  local url="$2"
  local field="$3"
  local expected="$4"

  local response
  response=$(curl -s --max-time 10 "$url" || echo "{}")
  local actual
  actual=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('${field}','MISSING'))" 2>/dev/null || echo "PARSE_ERROR")

  if [[ "$actual" == "$expected" ]]; then
    log_pass "${name} → ${field}=${actual}"
  else
    log_fail "${name} → Expected ${field}=${expected}, got ${actual}"
    FAILURES=$(( FAILURES + 1 ))
  fi
}

# ── 1. 容器状态检查 ───────────────────────────────────────────────────────────
echo "── 1. Container Status ──────────────────────────────────────────────────"
check_container "Backend"  "hivemind-backend-${TARGET_SLOT}"
check_container "Postgres" "hivemind-postgres-${TARGET_SLOT}"
check_container "Redis"    "hivemind-redis-${TARGET_SLOT}"
check_container "Chroma"   "hivemind-chroma-${TARGET_SLOT}"
check_container "MinIO"    "hivemind-minio-${TARGET_SLOT}"
echo ""

# ── 2. API 端点健康检查 ───────────────────────────────────────────────────────
echo "── 2. API Endpoint Health ───────────────────────────────────────────────"
check_http "Health endpoint"    "${BASE_URL}/health/"
check_http "Frontend (Nginx)"   "http://localhost:${FRONTEND_PORT}"
check_http "API docs (OpenAPI)" "${BASE_URL}/docs"  200
echo ""

# ── 3. 关键 API 响应内容验证 ──────────────────────────────────────────────────
echo "── 3. API Response Validation ───────────────────────────────────────────"
check_json_field "Health status field" "${BASE_URL}/health/" "status" "ok"
echo ""

# ── 4. 数据库连通性（通过 API 间接验证）──────────────────────────────────────
echo "── 4. Database Connectivity ─────────────────────────────────────────────"
log_info "Checking DB via backend container exec..."
db_check=$(docker exec "hivemind-backend-${TARGET_SLOT}" \
  python3 -c "
import asyncio, sys
async def check():
    try:
        from app.sdk.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        print('ok')
    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        sys.exit(1)
asyncio.run(check())
" 2>&1 || echo "error")

if [[ "$db_check" == "ok" ]]; then
  log_pass "Database connectivity → ok"
else
  log_fail "Database connectivity → ${db_check}"
  FAILURES=$(( FAILURES + 1 ))
fi
echo ""

# ── 5. Redis 连通性 ───────────────────────────────────────────────────────────
echo "── 5. Redis Connectivity ────────────────────────────────────────────────"
redis_check=$(docker exec "hivemind-redis-${TARGET_SLOT}" \
  redis-cli ping 2>/dev/null || echo "FAILED")

if [[ "$redis_check" == "PONG" ]]; then
  log_pass "Redis PING → PONG"
else
  log_fail "Redis PING → ${redis_check}"
  FAILURES=$(( FAILURES + 1 ))
fi
echo ""

# ── 6. 完整检查（可选）：LLM 路由冒烟测试 ────────────────────────────────────
if [[ "$FULL_CHECK" == "true" ]]; then
  echo "── 6. LLM Router Smoke Test (Full Mode) ─────────────────────────────────"
  log_warn "Full check requires valid LLM_API_KEY in environment."

  llm_check=$(curl -s --max-time 30 \
    -X POST "${BASE_URL}/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${LLM_API_KEY:-sk-test}" \
    -d '{"messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
    -o /dev/null -w "%{http_code}" || echo "000")

  if [[ "$llm_check" == "200" ]]; then
    log_pass "LLM Router → HTTP ${llm_check}"
  else
    log_warn "LLM Router → HTTP ${llm_check} (may be expected without valid API key)"
  fi
  echo ""
fi

# ── 结果汇总 ──────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$FAILURES" -eq 0 ]]; then
  echo -e "${GREEN}  ✅ All checks PASSED — Slot '${TARGET_SLOT}' is healthy${NC}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo -e "${RED}  ❌ ${FAILURES} check(s) FAILED — Review output above${NC}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi
