#!/bin/bash
# OpenClaw agent bench: run inference then evaluation.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$WORKSPACE_DIR" || exit 1
export PYTHONPATH="$WORKSPACE_DIR:$PROJECT_DIR:$PYTHONPATH"

# OPENAI_API_KEY must be provided by environment or config.

if [[ -z "${OPENCLAW_BIN:-}" ]]; then
  if command -v openclaw >/dev/null 2>&1; then
    export OPENCLAW_BIN="$(command -v openclaw)"
  elif [[ -x "$HOME/.npm-global/bin/openclaw" ]]; then
    export OPENCLAW_BIN="$HOME/.npm-global/bin/openclaw"
  fi
fi

# Default skills root: /home/sunxiangyu/sunxiangyu/nanobot_test/skills
DEFAULT_SKILLS_ROOT="$(cd "$WORKSPACE_DIR/.." && pwd)/skills"
USE_SKILLS="${USE_SKILLS:-True}"
case "${USE_SKILLS,,}" in
  false|0|no|off)
    export DRUGAGENT_SKILLS_ROOT="${DRUGAGENT_SKILLS_ROOT:-/tmp/__disable_project_skills__}"
    ;;
  *)
    if [[ -d "$DEFAULT_SKILLS_ROOT" ]]; then
      export DRUGAGENT_SKILLS_ROOT="${DRUGAGENT_SKILLS_ROOT:-$DEFAULT_SKILLS_ROOT}"
    fi
    ;;
esac

# Align OpenClaw native skill lookup path with project skills.
OPENCLAW_NATIVE_SKILLS_DIR="$HOME/.npm-global/lib/node_modules/openclaw/skills"
if [[ -d "$OPENCLAW_NATIVE_SKILLS_DIR" && -d "$DEFAULT_SKILLS_ROOT" ]]; then
  case "${USE_SKILLS,,}" in
    false|0|no|off)
      # Remove project skill mirrors so OpenClaw cannot see them when disabled.
      for skill_dir in "$DEFAULT_SKILLS_ROOT"/*; do
        [[ -d "$skill_dir" ]] || continue
        skill_name="$(basename "$skill_dir")"
        target="$OPENCLAW_NATIVE_SKILLS_DIR/$skill_name"
        if [[ -L "$target" ]]; then
          rm -f "$target"
        elif [[ -d "$target" ]]; then
          rm -rf "$target"
        fi
      done
      ;;
  esac
fi

if [[ -n "${DRUGAGENT_SKILLS_ROOT:-}" && -d "${DRUGAGENT_SKILLS_ROOT}" ]]; then
  mkdir -p "$(dirname "$OPENCLAW_NATIVE_SKILLS_DIR")"
  if [[ -L "$OPENCLAW_NATIVE_SKILLS_DIR" ]]; then
    current_target="$(readlink "$OPENCLAW_NATIVE_SKILLS_DIR" || true)"
    if [[ "$current_target" != "$DRUGAGENT_SKILLS_ROOT" ]]; then
      rm -f "$OPENCLAW_NATIVE_SKILLS_DIR"
      ln -s "$DRUGAGENT_SKILLS_ROOT" "$OPENCLAW_NATIVE_SKILLS_DIR"
    fi
  elif [[ ! -e "$OPENCLAW_NATIVE_SKILLS_DIR" ]]; then
    ln -s "$DRUGAGENT_SKILLS_ROOT" "$OPENCLAW_NATIVE_SKILLS_DIR"
  fi

  # If the native skills dir is a real directory (default npm install),
  # copy each project skill into it. OpenClaw may skip symlinked skill paths
  # that resolve outside the configured root.
  if [[ -d "$OPENCLAW_NATIVE_SKILLS_DIR" ]]; then
    for skill_dir in "$DRUGAGENT_SKILLS_ROOT"/*; do
      [[ -d "$skill_dir" ]] || continue
      skill_name="$(basename "$skill_dir")"
      target="$OPENCLAW_NATIVE_SKILLS_DIR/$skill_name"
      if [[ -L "$target" ]]; then
        rm -f "$target"
        cp -a "$skill_dir" "$target"
      elif [[ ! -e "$target" ]]; then
        cp -a "$skill_dir" "$target"
      fi
    done
  fi
fi

CFG_FILE="openclaw_template.yaml"

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
      echo "Usage: bash launch_openclaw.sh [--cfg yaml_name_or_path]"
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1"
      echo "Usage: bash launch_openclaw.sh [--cfg yaml_name_or_path]"
      exit 1
      ;;
  esac
done

if [[ "$CFG_FILE" = /* ]]; then
  RESOLVED_CFG="$CFG_FILE"
elif [[ -f "$CFG_FILE" ]]; then
  RESOLVED_CFG="$CFG_FILE"
elif [[ -f "$WORKSPACE_DIR/config/$CFG_FILE" ]]; then
  RESOLVED_CFG="$WORKSPACE_DIR/config/$CFG_FILE"
elif [[ "$CFG_FILE" == config/* && -f "$WORKSPACE_DIR/$CFG_FILE" ]]; then
  RESOLVED_CFG="$WORKSPACE_DIR/$CFG_FILE"
else
  RESOLVED_CFG="$CFG_FILE"
fi

if [[ ! -f "$RESOLVED_CFG" ]]; then
  echo "Error: config file not found: $CFG_FILE"
  exit 1
fi

PYTHONUNBUFFERED=1 python "$PROJECT_DIR/infer/openclaw_agent/run_openclaw.py" --cfg "$RESOLVED_CFG" 2>&1 | tee /tmp/run_openclaw_out.txt
[ ${PIPESTATUS[0]} -ne 0 ] && exit ${PIPESTATUS[0]}

RESULTS_DIR=$(grep '^RESULTS_DIR=' /tmp/run_openclaw_out.txt | tail -1 | sed 's/^RESULTS_DIR=//')
if [[ -z "$RESULTS_DIR" ]]; then
  echo "Error: run_openclaw did not emit RESULTS_DIR=..."
  exit 1
fi

python "$PROJECT_DIR/evaluate/run_eval_bench.py" "$RESULTS_DIR" --cfg "$RESOLVED_CFG"
