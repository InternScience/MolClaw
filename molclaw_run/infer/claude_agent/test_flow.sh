#!/bin/bash
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

LOG_FILE="$SCRIPT_DIR/test_flow_claude_log.txt"
: > "$LOG_FILE"

CLAUDE_MODE="${1:-non}"
CLAUDE_BIN="${2:-claude}"
fail_count=0

cfg_list=(
  "claude_template.yaml"
)

echo "===== claude test_flow start: $(date '+%F %T') =====" | tee -a "$LOG_FILE"
echo "===== claude_mode: $CLAUDE_MODE =====" | tee -a "$LOG_FILE"
echo "===== claude_bin: $CLAUDE_BIN =====" | tee -a "$LOG_FILE"

for cfg in "${cfg_list[@]}"; do
  echo | tee -a "$LOG_FILE"
  echo "===== Running: bash launch_claude.sh --cfg $cfg --claude-mode $CLAUDE_MODE --claude-bin $CLAUDE_BIN =====" | tee -a "$LOG_FILE"
  bash launch_claude.sh \
    --cfg "$cfg" \
    --claude-mode "$CLAUDE_MODE" \
    --claude-bin "$CLAUDE_BIN" 2>&1 | tee -a "$LOG_FILE"
  cmd_status=${PIPESTATUS[0]}
  echo "===== Exit code: $cmd_status for cfg=$cfg =====" | tee -a "$LOG_FILE"
  if [[ "$cmd_status" -ne 0 ]]; then
    fail_count=$((fail_count + 1))
  fi
done

echo | tee -a "$LOG_FILE"
echo "===== claude test_flow end: $(date '+%F %T') | failed_cfgs=$fail_count =====" | tee -a "$LOG_FILE"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi

# 用法: bash test_flow_claude.sh [claude_mode] [claude_bin]
# claude_mode: non|both，默认 non（无 skills 可见模式）
