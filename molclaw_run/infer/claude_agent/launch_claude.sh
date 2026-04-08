#!/bin/bash
# claude infer -> eval

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLM_BENCH_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$WORKSPACE_DIR" || exit 1

export PYTHONPATH="$WORKSPACE_DIR${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH="$LLM_BENCH_DIR${PYTHONPATH:+:$PYTHONPATH}"

CFG_FILE="claude_template.yaml"
CLAUDE_MODE="both"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cfg)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --cfg requires a value."
        exit 1
      fi
      CFG_FILE="$2"
      shift 2
      ;;
    --claude-mode)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --claude-mode requires a value."
        exit 1
      fi
      CLAUDE_MODE="$2"
      shift 2
      ;;
    --claude-bin)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --claude-bin requires a value."
        exit 1
      fi
      CLAUDE_BIN="$2"
      shift 2
      ;;
    --claude-extra-arg)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --claude-extra-arg requires a value."
        exit 1
      fi
      CLAUDE_EXTRA_ARGS+=("$2")
      shift 2
      ;;
    -h|--help)
      echo "Usage: bash launch_claude.sh [--cfg yaml_name_or_path] [--claude-mode non|both] [--claude-bin path_or_name] [--claude-extra-arg ARG ...]"
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1"
      echo "Usage: bash launch_claude.sh [--cfg yaml_name_or_path] [--claude-mode non|both] [--claude-bin path_or_name] [--claude-extra-arg ARG ...]"
      exit 1
      ;;
  esac
done

if [[ "$CLAUDE_MODE" != "non" && "$CLAUDE_MODE" != "both" ]]; then
  echo "Error: --claude-mode must be one of: non, both"
  exit 1
fi

if [[ "$CFG_FILE" = /* ]]; then
  resolved_cfg="$CFG_FILE"
elif [[ -f "$CFG_FILE" ]]; then
  resolved_cfg="$CFG_FILE"
elif [[ -f "$LLM_BENCH_DIR/config/$CFG_FILE" ]]; then
  resolved_cfg="$LLM_BENCH_DIR/config/$CFG_FILE"
elif [[ "$CFG_FILE" == config/* && -f "$LLM_BENCH_DIR/$CFG_FILE" ]]; then
  resolved_cfg="$LLM_BENCH_DIR/$CFG_FILE"
else
  resolved_cfg="$CFG_FILE"
fi

if [[ ! -f "$resolved_cfg" ]]; then
  echo "Error: config file not found: $CFG_FILE"
  exit 1
fi
CFG_FILE="$resolved_cfg"

cmd=(
  python "$LLM_BENCH_DIR/infer/claude_agent/run_claude.py"
  --cfg "$CFG_FILE"
  --claude-mode "$CLAUDE_MODE"
  --claude-bin "$CLAUDE_BIN"
)
if [[ ${#CLAUDE_EXTRA_ARGS[@]} -gt 0 ]]; then
  cmd+=(--claude-extra-args "${CLAUDE_EXTRA_ARGS[@]}")
fi

PYTHONUNBUFFERED=1 "${cmd[@]}" 2>&1 | tee /tmp/run_claude_out.txt
py_status=${PIPESTATUS[0]}
[ "$py_status" -ne 0 ] && exit "$py_status"

captured=$(grep '^RESULTS_DIR=' /tmp/run_claude_out.txt | tail -1 | sed 's/^RESULTS_DIR=//')
if [ -z "$captured" ]; then
  echo "Error: run_claude did not emit RESULTS_DIR=...; inference likely failed."
  exit 1
fi
results_dir="$captured"

python "$WORKSPACE_DIR/molbench/eval/run_eval_bench.py" "$results_dir" --cfg "$CFG_FILE"
