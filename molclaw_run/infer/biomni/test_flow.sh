#!/bin/bash
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

LOG_FILE="$SCRIPT_DIR/test_flow_log.txt"
: > "$LOG_FILE"

cfg_list=(
  "biomni_template.yaml"
)

echo "===== biomni test_flow start: $(date '+%F %T') =====" | tee -a "$LOG_FILE"

for cfg in "${cfg_list[@]}"; do
  echo | tee -a "$LOG_FILE"
  echo "===== Running: bash launch_biomni.sh --cfg $cfg =====" | tee -a "$LOG_FILE"
  bash launch_biomni.sh --cfg "$cfg" 2>&1 | tee -a "$LOG_FILE"
  cmd_status=${PIPESTATUS[0]}
  echo "===== Exit code: $cmd_status for cfg=$cfg =====" | tee -a "$LOG_FILE"
done

echo | tee -a "$LOG_FILE"
echo "===== biomni test_flow end: $(date '+%F %T') =====" | tee -a "$LOG_FILE"
