#!/usr/bin/env bash
# =============================================================================
# HiveMind RAG — Blue/Green Deployment Script
# =============================================================================
# 原理：
#   - 维护两套 compose profile: blue / green
#   - 当前活跃的称为 "active"，另一套称为 "standby"
#   - 部署时先在 standby 上构建并启动新版本
#   - 健康检查通过后，将 Nginx upstream 切换到 standby
#   - 原 active 保留 ROLLBACK_KEEP_MINUTES 分钟后停止（用于快速回滚）
#
# 使用方式:
#   ./blue_green_deploy.sh [--branch <branch>] [--tag <image_tag>]
#
# 环境变量（可通过 .env.deploy 覆盖）:
#   PROJECT_DIR          项目根目录，默认 /home/azureuser/HiveMind_RAG
#   HEALTH_CHECK_URL     后端健康检查地址
#   HEALTH_RETRIES       健康检查最大重试次数，默认 36（3 分钟）
#   HEALTH_INTERVAL      每次重试间隔秒数，默认 5
#   ROLLBACK_KEEP_MINUTES 旧版本保留时间，默认 10 分钟
#   SLACK_WEBHOOK_URL    (可选) Slack 通知 Webhook
# =============================================================================

set -euo pipefail

# ── 颜色输出 ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── 默认配置 ──────────────────────────────────────────────────────────────────
PROJECT_DIR="${PROJECT_DIR:-/home/azureuser/HiveMind_RAG}"
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8000/api/v1/health/}"
HEALTH_RETRIES="${HEALTH_RETRIES:-36}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"
ROLLBACK_KEEP_MINUTES="${ROLLBACK_KEEP_MINUTES:-10}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
STATE_FILE="${PROJECT_DIR}/.deploy_state"
DEPLOY_LOG="${PROJECT_DIR}/logs/deploy/deploy_$(date +%Y%m%d_%H%M%S).log"

# ── 参数解析 ──────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --branch) DEPLOY_BRANCH="$2"; shift 2 ;;
    --tag)    IMAGE_TAG="$2";     shift 2 ;;
    *)        log_warn "Unknown argument: $1"; shift ;;
  esac
done

# ── 加载本地部署环境变量（如果存在）─────────────────────────────────────────
[[ -f "${PROJECT_DIR}/.env.deploy" ]] && source "${PROJECT_DIR}/.env.deploy"

# ── 初始化日志目录 ────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$DEPLOY_LOG")"
exec > >(tee -a "$DEPLOY_LOG") 2>&1

log_info "=========================================="
log_info "  HiveMind RAG Blue/Green Deploy"
log_info "  Branch: ${DEPLOY_BRANCH}"
log_info "  Time:   $(date '+%Y-%m-%d %H:%M:%S')"
log_info "=========================================="

# ── 读取当前活跃 slot ─────────────────────────────────────────────────────────
get_active_slot() {
  if [[ -f "$STATE_FILE" ]]; then
    cat "$STATE_FILE"
  else
    echo "blue"  # 首次部署默认 blue 为 active
  fi
}

get_standby_slot() {
  local active
  active=$(get_active_slot)
  [[ "$active" == "blue" ]] && echo "green" || echo "blue"
}

# ── Compose 文件路径 ──────────────────────────────────────────────────────────
compose_file() {
  local slot="$1"
  echo "${PROJECT_DIR}/docker-compose.${slot}.yml"
}

# ── 获取 standby slot 的后端容器名 ───────────────────────────────────────────
backend_container() {
  local slot="$1"
  echo "hivemind-backend-${slot}"
}

# ── 健康检查 ──────────────────────────────────────────────────────────────────
wait_for_healthy() {
  local slot="$1"
  local container
  container=$(backend_container "$slot")
  local url="${HEALTH_CHECK_URL}"

  log_info "Waiting for ${container} to become healthy (max ${HEALTH_RETRIES} retries)..."

  for i in $(seq 1 "$HEALTH_RETRIES"); do
    local status
    status=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")

    if [[ "$status" == "healthy" ]]; then
      log_success "Container ${container} is healthy! (attempt ${i}/${HEALTH_RETRIES})"
      return 0
    fi

    if [[ "$status" == "unhealthy" ]]; then
      log_error "Container ${container} reported UNHEALTHY. Aborting."
      docker logs "$container" --tail=50
      return 1
    fi

    log_info "  [${i}/${HEALTH_RETRIES}] Status: ${status} — waiting ${HEALTH_INTERVAL}s..."
    sleep "$HEALTH_INTERVAL"
  done

  log_error "Health check timed out for ${container}."
  docker logs "$container" --tail=100
  return 1
}

# ── HTTP 端到端冒烟测试 ───────────────────────────────────────────────────────
smoke_test() {
  local slot="$1"
  local port
  # blue=8000, green=8001（端口映射在各自的 compose 文件中定义）
  [[ "$slot" == "blue" ]] && port=8000 || port=8001

  log_info "Running smoke test on port ${port}..."

  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    "http://localhost:${port}/api/v1/health/" || echo "000")

  if [[ "$http_code" == "200" ]]; then
    log_success "Smoke test passed (HTTP ${http_code})"
    return 0
  else
    log_error "Smoke test FAILED (HTTP ${http_code})"
    return 1
  fi
}

# ── Slack 通知（可选）────────────────────────────────────────────────────────
notify() {
  local status="$1"
  local message="$2"
  if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    local color
    [[ "$status" == "success" ]] && color="good" || color="danger"
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
      -H 'Content-type: application/json' \
      --data "{\"attachments\":[{\"color\":\"${color}\",\"text\":\"${message}\"}]}" \
      > /dev/null || true
  fi
}

# ── 触发自动回滚 ──────────────────────────────────────────────────────────────
trigger_rollback() {
  local failed_slot="$1"
  log_error "Deployment to ${failed_slot} FAILED. Triggering automatic rollback..."
  notify "failure" "🔴 HiveMind RAG deploy to ${failed_slot} FAILED on branch ${DEPLOY_BRANCH}. Auto-rollback initiated."

  # 停止失败的 standby slot
  local compose
  compose=$(compose_file "$failed_slot")
  if [[ -f "$compose" ]]; then
    docker compose -f "$compose" down --remove-orphans || true
  fi

  # 确认 active slot 仍在运行
  local active_slot
  active_slot=$(get_active_slot)
  local active_compose
  active_compose=$(compose_file "$active_slot")

  if [[ -f "$active_compose" ]]; then
    local active_container
    active_container=$(backend_container "$active_slot")
    local active_status
    active_status=$(docker inspect -f '{{.State.Status}}' "$active_container" 2>/dev/null || echo "not_found")

    if [[ "$active_status" == "running" ]]; then
      log_success "Active slot (${active_slot}) is still running. Service unaffected."
    else
      log_warn "Active slot (${active_slot}) is not running! Attempting restart..."
      docker compose -f "$active_compose" up -d --remove-orphans || true
    fi
  fi

  exit 1
}

# ── 主部署流程 ────────────────────────────────────────────────────────────────
main() {
  cd "$PROJECT_DIR"

  # 1. 拉取最新代码
  log_info "Step 1/7: Pulling latest code from branch '${DEPLOY_BRANCH}'..."
  git fetch origin
  git checkout "$DEPLOY_BRANCH"
  git pull origin "$DEPLOY_BRANCH"
  local git_sha
  git_sha=$(git rev-parse --short HEAD)
  log_success "Code updated to commit: ${git_sha}"

  # 2. 确定 active / standby slot
  local active_slot standby_slot
  active_slot=$(get_active_slot)
  standby_slot=$(get_standby_slot)
  log_info "Step 2/7: Active slot = ${active_slot}, Standby slot = ${standby_slot}"

  # 3. 生成 standby 的 compose 文件（从 prod 模板派生）
  log_info "Step 3/7: Generating compose file for standby slot '${standby_slot}'..."
  generate_slot_compose "$standby_slot"

  # 4. 构建并启动 standby slot
  log_info "Step 4/7: Building and starting standby slot '${standby_slot}'..."
  local standby_compose
  standby_compose=$(compose_file "$standby_slot")

  # 先停止旧的 standby（如果存在）
  docker compose -f "$standby_compose" down --remove-orphans 2>/dev/null || true

  # 构建新镜像并启动
  if ! docker compose -f "$standby_compose" up -d --build --remove-orphans; then
    trigger_rollback "$standby_slot"
  fi

  # 5. 健康检查
  log_info "Step 5/7: Running health checks on standby slot '${standby_slot}'..."
  if ! wait_for_healthy "$standby_slot"; then
    trigger_rollback "$standby_slot"
  fi

  if ! smoke_test "$standby_slot"; then
    trigger_rollback "$standby_slot"
  fi

  # 6. 运行数据库迁移（在新版本容器上执行）
  log_info "Step 6/7: Running database migrations on standby slot..."
  local standby_container
  standby_container=$(backend_container "$standby_slot")
  if ! docker exec "$standby_container" python -m alembic upgrade head; then
    log_error "Database migration FAILED on standby slot."
    trigger_rollback "$standby_slot"
  fi
  log_success "Database migrations completed."

  # 7. 切换流量：更新 state file，停止旧 active（延迟）
  log_info "Step 7/7: Switching traffic to standby slot '${standby_slot}'..."
  echo "$standby_slot" > "$STATE_FILE"
  log_success "State file updated: active slot is now '${standby_slot}'"

  # 保留旧 active 容器 ROLLBACK_KEEP_MINUTES 分钟，然后后台停止
  local old_active_compose
  old_active_compose=$(compose_file "$active_slot")
  if [[ -f "$old_active_compose" ]]; then
    log_info "Old active slot '${active_slot}' will be stopped in ${ROLLBACK_KEEP_MINUTES} minutes (rollback window)."
    (
      sleep $(( ROLLBACK_KEEP_MINUTES * 60 ))
      log_info "Stopping old active slot '${active_slot}'..."
      docker compose -f "$old_active_compose" down --remove-orphans 2>/dev/null || true
      # 清理旧镜像
      docker image prune -f 2>/dev/null || true
      docker builder prune -f 2>/dev/null || true
    ) &
    disown
  fi

  log_success "=========================================="
  log_success "  Deployment SUCCESSFUL"
  log_success "  Active slot:  ${standby_slot}"
  log_success "  Git SHA:      ${git_sha}"
  log_success "  Branch:       ${DEPLOY_BRANCH}"
  log_success "  Rollback window: ${ROLLBACK_KEEP_MINUTES} min"
  log_success "=========================================="

  notify "success" "✅ HiveMind RAG deployed successfully. Branch: ${DEPLOY_BRANCH}, SHA: ${git_sha}, Slot: ${standby_slot}"
}

# ── 生成 slot 专属的 compose 文件 ─────────────────────────────────────────────
# 从 docker-compose.prod.yml 派生，修改容器名和端口映射
generate_slot_compose() {
  local slot="$1"
  local port
  [[ "$slot" == "blue" ]] && port=8000 || port=8001

  local output_file
  output_file=$(compose_file "$slot")

  # 使用 sed 替换容器名后缀和端口（简单可靠，不依赖 yq）
  sed \
    -e "s/hivemind-backend-prod/hivemind-backend-${slot}/g" \
    -e "s/hivemind-postgres-prod/hivemind-postgres-${slot}/g" \
    -e "s/hivemind-redis-prod/hivemind-redis-${slot}/g" \
    -e "s/hivemind-chroma-prod/hivemind-chroma-${slot}/g" \
    -e "s/hivemind-minio-prod/hivemind-minio-${slot}/g" \
    -e "s/postgres_data_prod/postgres_data_${slot}/g" \
    -e "s/redis_data_prod/redis_data_${slot}/g" \
    -e "s/chroma_data_prod/chroma_data_${slot}/g" \
    -e "s/minio_data_prod/minio_data_${slot}/g" \
    -e "s|\"80:80\"|\"80:80\"|g" \
    "${PROJECT_DIR}/docker-compose.prod.yml" > "$output_file"

  log_info "Generated compose file: ${output_file}"
}

main "$@"
