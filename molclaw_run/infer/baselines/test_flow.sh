#!/bin/bash
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

LOG_FILE="$SCRIPT_DIR/test_flow_log.txt"
: > "$LOG_FILE"

# cfg_list=(
#   "launch_rdkit_qwen3.5-plus.yaml"
#   "launch_rdkit_claude-haiku-4-5-20251001.yaml"
#   "launch_rdkit_meta-llama_llama-3.1-70b-instruct.yaml"
#   "launch_rdkit_deepseek-v3.2.yaml"
#   "launch_rdkit_gemini-3-flash-preview-nothinking.yaml"
# )

cfg_list=(
  "baseline_molbench-ms-1.yaml"
  "baseline_molbench-ms-2.yaml"
  "baseline_molbench-ms-3.yaml"
  "chemcot_mo_edit.yaml"
  "chemcot_mo_opt.yaml"
)

echo "===== baseline test_flow start: $(date '+%F %T') =====" | tee -a "$LOG_FILE"

fail_count=0

for cfg in "${cfg_list[@]}"; do
  echo | tee -a "$LOG_FILE"
  echo "===== Running: bash launch_baseline.sh --cfg $cfg =====" | tee -a "$LOG_FILE"
  bash launch_baseline.sh --cfg "$cfg" 2>&1 | tee -a "$LOG_FILE"
  cmd_status=${PIPESTATUS[0]}
  echo "===== Exit code: $cmd_status for cfg=$cfg =====" | tee -a "$LOG_FILE"
  if [[ "$cmd_status" -ne 0 ]]; then
    fail_count=$((fail_count + 1))
  fi
done

echo | tee -a "$LOG_FILE"
echo "===== baseline test_flow end: $(date '+%F %T') | failed_cfgs=$fail_count =====" | tee -a "$LOG_FILE"

if [[ "$fail_count" -ne 0 ]]; then
  exit 1
fi
