#!/usr/bin/env bash
# =============================================================================
# HiveMind RAG — Manual Rollback Script
# =============================================================================
# 用途：在部署后发现问题时，手动触发回滚到上一个 slot
#
# 使用方式:
#   ./rollback.sh                    # 回滚到上一个 slot（自动判断）
#   ./rollback.sh --slot blue        # 强制回滚到指定 slot
#   ./rollback.sh --dry-run          # 仅打印操作，不执行
#
# 前提：
#   - blue_green_deploy.sh 已至少成功运行过一次
#   - 旧 slot 的容器仍在运行（在 ROLLBACK_KEEP_MINUTES 窗口内）
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

PROJECT_DIR="${PROJECT_DIR:-/home/azureuser/HiveMind_RAG}"
STATE_FILE="${PROJECT_DIR}/.deploy_state"
DRY_RUN=false
TARGET_SLOT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --slot)    TARGET_SLOT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *)         log_warn "Unknown argument: $1"; shift ;;
  esac
done

# ── 读取当前状态 ──────────────────────────────────────────────────────────────
if [[ ! -f "$STATE_FILE" ]]; then
  log_error "State file not found: ${STATE_FILE}"
  log_error "No deployment history found. Cannot rollback."
  exit 1
fi

current_active=$(cat "$STATE_FILE")
if [[ -z "$TARGET_SLOT" ]]; then
  # 自动判断：回滚到另一个 slot
  [[ "$current_active" == "blue" ]] && TARGET_SLOT="green" || TARGET_SLOT="blue"
fi

log_info "=========================================="
log_info "  HiveMind RAG Rollback"
log_info "  Current active: ${current_active}"
log_info "  Rollback to:    ${TARGET_SLOT}"
log_info "  Dry run:        ${DRY_RUN}"
log_info "=========================================="

# ── 检查目标 slot 的容器是否存在且运行 ───────────────────────────────────────
target_container="hivemind-backend-${TARGET_SLOT}"
target_status=$(docker inspect -f '{{.State.Status}}' "$target_container" 2>/dev/null || echo "not_found")

if [[ "$target_status" == "not_found" ]]; then
  log_error "Target container '${target_container}' not found."
  log_error "The rollback window may have expired (container was already stopped)."
  log_error "You need to redeploy the previous version manually."
  exit 1
fi

if [[ "$target_status" != "running" ]]; then
  log_warn "Target container '${target_container}' exists but is not running (status: ${target_status})."
  log_info "Attempting to start it..."
  if [[ "$DRY_RUN" == "false" ]]; then
    target_compose="${PROJECT_DIR}/docker-compose.${TARGET_SLOT}.yml"
    if [[ -f "$target_compose" ]]; then
      docker compose -f "$target_compose" up -d
    else
      log_error "Compose file not found: ${target_compose}"
      exit 1
    fi
  fi
fi

# ── 健康检查目标 slot ─────────────────────────────────────────────────────────
[[ "$TARGET_SLOT" == "blue" ]] && target_port=8000 || target_port=8001

log_info "Verifying target slot health on port ${target_port}..."
if [[ "$DRY_RUN" == "false" ]]; then
  http_code=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    "http://localhost:${target_port}/api/v1/health/" || echo "000")

  if [[ "$http_code" != "200" ]]; then
    log_error "Target slot health check FAILED (HTTP ${http_code})."
    log_error "Cannot rollback to an unhealthy slot."
    exit 1
  fi
  log_success "Target slot is healthy (HTTP ${http_code})"
fi

# ── 执行回滚 ──────────────────────────────────────────────────────────────────
log_info "Switching active slot from '${current_active}' to '${TARGET_SLOT}'..."

if [[ "$DRY_RUN" == "true" ]]; then
  log_warn "[DRY RUN] Would update state file: ${STATE_FILE} → ${TARGET_SLOT}"
  log_warn "[DRY RUN] Would stop current active slot: ${current_active}"
else
  # 更新 state file
  echo "$TARGET_SLOT" > "$STATE_FILE"
  log_success "State file updated: active slot is now '${TARGET_SLOT}'"

  # 停止当前（有问题的）active slot
  current_compose="${PROJECT_DIR}/docker-compose.${current_active}.yml"
  if [[ -f "$current_compose" ]]; then
    log_info "Stopping problematic slot '${current_active}'..."
    docker compose -f "$current_compose" down --remove-orphans || true
    log_success "Slot '${current_active}' stopped."
  fi
fi

log_success "=========================================="
log_success "  Rollback SUCCESSFUL"
log_success "  Active slot is now: ${TARGET_SLOT}"
log_success "=========================================="
log_info "Next steps:"
log_info "  1. Investigate the issue in the failed deployment"
log_info "  2. Fix the code and push a new deployment"
log_info "  3. Monitor logs: tail -f ${PROJECT_DIR}/logs/deploy/*.log"
