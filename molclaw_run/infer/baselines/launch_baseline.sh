#!/bin/bash
# Direct LLM baseline: same input/eval as agent. Run inference then eval.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_space="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$work_space" || exit 1
export PYTHONPATH="$work_space${PYTHONPATH:+:$PYTHONPATH}"

# Default config (can be overridden by --cfg)
CFG_FILE="baseline_molbench-ms-1.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cfg)
      if [[ -z "$2" ]]; then
        echo "Error: --cfg requires a value."
        exit 1
      fi
      CFG_FILE="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: bash launch_baseline.sh [--cfg yaml_name_or_path]"
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1"
      echo "Usage: bash launch_baseline.sh [--cfg yaml_name_or_path]"
      exit 1
      ;;
  esac
done

if [[ "$CFG_FILE" = /* ]]; then
  resolved_cfg="$CFG_FILE"
elif [[ -f "$CFG_FILE" ]]; then
  resolved_cfg="$CFG_FILE"
elif [[ -f "$work_space/config/$CFG_FILE" ]]; then
  resolved_cfg="$work_space/config/$CFG_FILE"
elif [[ "$CFG_FILE" == config/* && -f "$work_space/$CFG_FILE" ]]; then
  resolved_cfg="$work_space/$CFG_FILE"
else
  resolved_cfg="$CFG_FILE"
fi

if [[ ! -f "$resolved_cfg" ]]; then
  echo "Error: config file not found: $CFG_FILE"
  exit 1
fi

CFG_FILE="$resolved_cfg"

# run_step1=1: run baseline inference, then eval; run_step1=0: eval only (set results_dir below)
run_step1=1

# For eval-only, set results_dir to a baseline_run_* dir
# results_dir="/path/to/results/agent_prediction/baseline_run_YYYYMMDD_HHMMSS"

if [ "$run_step1" = 1 ]; then
  PYTHONUNBUFFERED=1 python molclaw_run/infer/baselines/run_baseline.py --cfg "$CFG_FILE" 2>&1 | tee /tmp/run_baseline_out.txt
  py_status=${PIPESTATUS[0]}
  if [ "$py_status" -ne 0 ]; then
    echo "Error: run_baseline.py failed with exit code $py_status"
    exit "$py_status"
  fi
  captured=$(grep '^RESULTS_DIR=' /tmp/run_baseline_out.txt | tail -1 | sed 's/^RESULTS_DIR=//')
  if [ -z "$captured" ]; then
    echo "Error: run_baseline did not emit RESULTS_DIR=...; inference likely failed."
    exit 1
  fi
  results_dir="$captured"
fi

[ -z "$results_dir" ] && { echo "Error: results_dir empty. Set run_step1=1 or set results_dir in script."; exit 1; }
python molclaw_run/evaluate/run_eval_bench.py "$results_dir" --cfg "$CFG_FILE"
