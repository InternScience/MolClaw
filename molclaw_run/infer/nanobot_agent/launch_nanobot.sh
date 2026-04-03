#!/bin/bash
# nanobot infer -> eval

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLM_BENCH_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
work_space="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$work_space" || exit 1

export PYTHONPATH="$work_space${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH="$LLM_BENCH_DIR${PYTHONPATH:+:$PYTHONPATH}"

# default cfg (can be overridden by --cfg)
CFG_FILE="nanobot_template.yaml"
NANOBOT_MODE="both"
MCP_URL="${NANOBOT_MCP_URL:-http://127.0.0.1:32208/mcp}"
MCP_API_KEY="${NANOBOT_MCP_API_KEY:-}"

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
    --nanobot-mode)
      if [[ -z "$2" ]]; then
        echo "Error: --nanobot-mode requires a value."
        exit 1
      fi
      NANOBOT_MODE="$2"
      shift 2
      ;;
    --mcp-url)
      if [[ -z "$2" ]]; then
        echo "Error: --mcp-url requires a value."
        exit 1
      fi
      MCP_URL="$2"
      shift 2
      ;;
    --mcp-api-key)
      if [[ -z "$2" ]]; then
        echo "Error: --mcp-api-key requires a value."
        exit 1
      fi
      MCP_API_KEY="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: bash launch_nanobot.sh [--cfg yaml_name_or_path] [--nanobot-mode non|tool|skills|both] [--mcp-url url] [--mcp-api-key key]"
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1"
      echo "Usage: bash launch_nanobot.sh [--cfg yaml_name_or_path] [--nanobot-mode non|tool|skills|both] [--mcp-url url] [--mcp-api-key key]"
      exit 1
      ;;
  esac
done

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

run_step1=1

if [ "$run_step1" = 1 ]; then
  PYTHONUNBUFFERED=1 python "$LLM_BENCH_DIR/infer/nanobot_agent/run_nanobot.py" \
    --cfg "$CFG_FILE" \
    --nanobot-mode "$NANOBOT_MODE" \
    --mcp-url "$MCP_URL" \
    --mcp-api-key "$MCP_API_KEY" 2>&1 | tee /tmp/run_nanobot_out.txt
  py_status=${PIPESTATUS[0]}
  [ "$py_status" -ne 0 ] && exit "$py_status"
  captured=$(grep '^RESULTS_DIR=' /tmp/run_nanobot_out.txt | tail -1 | sed 's/^RESULTS_DIR=//')
  if [ -z "$captured" ]; then
    echo "Error: run_nanobot did not emit RESULTS_DIR=...; inference likely failed."
    exit 1
  fi
  results_dir="$captured"
fi

[ -z "$results_dir" ] && { echo "Error: results_dir empty. Set run_step1=1 or set results_dir in script."; exit 1; }
python "$LLM_BENCH_DIR/evaluate/run_eval_bench.py" "$results_dir" --cfg "$CFG_FILE"
