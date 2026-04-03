from __future__ import annotations

import json
import os
import re
import subprocess
import shutil
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from MolClaw.molclaw_run.infer.openclaw_agent.openclaw_bridge import credentials as oc_credentials
from MolClaw.molclaw_run.infer.openclaw_agent.openclaw_bridge.workspace import ensure_workspace, workspace_root, drugsda_tools_extension_dir


@dataclass(frozen=True)
class OpenClawRun:
    text: str
    payloads: List[Dict[str, Any]]
    meta: Dict[str, Any]
    raw: Dict[str, Any]
    stderr: str
    console_trace: List[str]
    plugin_tool_events: List[str]
    builtin_tool_events: List[str]
    visible_builtin_tools: List[str]
    visible_professional_tools: List[str]
    observed_builtin_tool_use: bool


_RESET = "\033[0m"
_BLUE = "\033[34m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
# SYS/info lines: use a brighter gray/white to remain readable on dark terminals.
_DIM = "\033[37m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_BUILTIN_TOOL_NAMES = {
    "read",
    "edit",
    "write",
    "exec",
    "process",
    "browser",
    "canvas",
    "nodes",
    "cron",
}


def _c(text: str, color: str) -> str:
    return f"{color}{text}{_RESET}"


def _normalize_model_id(model: str) -> str:
    if "/" in (model or ""):
        return model
    return f"openai/{model}"

def _extract_json_object(text: str) -> Dict[str, Any]:
    s = (text or "").strip()
    if not s:
        raise ValueError("empty output")
    if s.startswith("{") and s.endswith("}"):
        return json.loads(s)
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        return json.loads(s[start : end + 1])
    return json.loads(s)


def _repo_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def openclaw_bin() -> str:
    env_bin = (os.getenv("OPENCLAW_BIN") or "").strip()
    if env_bin:
        return env_bin
    npm_global_bin = Path.home() / ".npm-global" / "bin" / "openclaw"
    if npm_global_bin.is_file():
        return str(npm_global_bin)
    bin_path = _repo_dir() / "pre_build" / "node_modules" / ".bin" / "openclaw"
    if bin_path.is_file():
        return str(bin_path)
    which_bin = shutil.which("openclaw")
    if which_bin:
        return which_bin
    return str(bin_path)


def _resolve_python_bin() -> str:
    return (os.getenv("DRUGSDA_PYTHON_BIN") or "").strip() or shutil.which("python3") or "python3"


def _safe_session_name(session_id: str) -> str:
    raw = (session_id or "").strip()
    if not raw:
        return "default"
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in raw)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "default"


def _runtime_root(session_id: str) -> Path:
    return _repo_dir() / ".openclaw" / "runtime_session" / _safe_session_name(session_id)


def _state_dir(session_id: str) -> str:
    return str(_runtime_root(session_id) / "state")


def _config_path(session_id: str) -> str:
    return str(_runtime_root(session_id) / "openclaw.json")


def _session_workspace_dir(session_id: str) -> str:
    return str(workspace_root(_repo_dir(), session_id=session_id))


def cleanup_session_artifacts(session_id: str) -> None:
    """Remove per-session runtime and workspace directories after a sample completes."""
    runtime_root = _runtime_root(session_id)
    workspace_dir = Path(_session_workspace_dir(session_id))
    if runtime_root.exists():
        shutil.rmtree(runtime_root, ignore_errors=True)
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)


def _record_builtin_tools_enabled() -> bool:
    raw = os.getenv("DRUGAGENT_RECORD_BUILTIN_TOOLS")
    if raw is None:
        return True
    value = raw.strip()
    if value not in {"0", "1"}:
        raise ValueError(f"invalid DRUGAGENT_RECORD_BUILTIN_TOOLS: {value}")
    return value == "1"


def _professional_tools_enabled() -> bool:
    raw = os.getenv("DRUGAGENT_ENABLE_PROFESSIONAL_TOOLS")
    if raw is None:
        return True
    value = raw.strip()
    if value not in {"0", "1"}:
        raise ValueError(f"invalid DRUGAGENT_ENABLE_PROFESSIONAL_TOOLS: {value}")
    return value == "1"


def _visible_tool_names(meta: Dict[str, Any]) -> List[str]:
    report = meta.get("systemPromptReport") if isinstance(meta, dict) else {}
    tools = report.get("tools") if isinstance(report, dict) else {}
    entries = tools.get("entries") if isinstance(tools, dict) else []
    out: List[str] = []
    if not isinstance(entries, list):
        return out
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            out.append(name.strip())
    return out


def _split_visible_tool_names(tool_names: List[str]) -> tuple[List[str], List[str]]:
    builtin = [name for name in tool_names if name in _BUILTIN_TOOL_NAMES]
    professional = [name for name in tool_names if name not in _BUILTIN_TOOL_NAMES]
    return builtin, professional


def _extract_builtin_tool_events(lines: List[str], builtin_tools: List[str]) -> List[str]:
    if not lines or not builtin_tools:
        return []
    builtin_pattern = re.compile(r"\b(" + "|".join(re.escape(name) for name in builtin_tools) + r")\b")
    event_markers = ("tool call", "tool_call", "tool use", "tool_use", "tool result", "client_operation")
    out: List[str] = []
    for line in lines:
        low = line.lower()
        if builtin_pattern.search(line) and any(marker in low for marker in event_markers):
            out.append(line)
    return out


def write_local_config(*, openai_base_url: str, model: str, timeout_seconds: int, workspace_dir: str, session_id: str) -> str:
    model = _normalize_model_id(model)
    repo_root = _repo_dir()
    runtime_root = _runtime_root(session_id)
    runtime_root.mkdir(parents=True, exist_ok=True)
    Path(_state_dir(session_id)).mkdir(parents=True, exist_ok=True)
    ws = ensure_workspace(repo_root, session_id=session_id)
    ext_dir = str(drugsda_tools_extension_dir(repo_root, session_id=session_id))
    plugins_cfg = {
            # Trust and enable our local extension that registers DrugSDA tools.
            "allow": ["drugsda-tools"],
            "load": {"paths": [ext_dir]},
            "entries": {
                "drugsda-tools": {
                    "enabled": True,
                    "config": {
                        # Pin an explicit python to avoid PATH surprises inside OpenClaw runtime.
                        "pythonBin": _resolve_python_bin(),
                        "timeoutMs": int(timeout_seconds * 1000),
                    },
                }
            },
    } if _professional_tools_enabled() else {}
    cfg = {
        "meta": {},
        "agents": {
            "defaults": {
                "model": {"primary": model},
                "workspace": workspace_dir,
                "repoRoot": str(repo_root),
            }
        },
        "models": {
            "providers": {
                "openai": {
                    "baseUrl": openai_base_url,
                    "api": "openai-completions",
                    "models": [
                        {
                            "id": model,
                            "name": model,
                            "api": "openai-completions",
                        }
                    ],
                }
            }
        }
    }
    if plugins_cfg:
        cfg["plugins"] = plugins_cfg
    path = _config_path(session_id)
    Path(path).write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _base_env(*, openai_api_key: str, openai_base_url: str, model: str, timeout_seconds: int, workspace_dir: str, session_id: str) -> Dict[str, str]:
    if not (openai_api_key or "").strip():
        raise RuntimeError("OPENAI_API_KEY is required for OpenClaw runs. Please export OPENAI_API_KEY before launch.")
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = openai_api_key
    env["OPENCLAW_STATE_DIR"] = _state_dir(session_id)
    env["DRUGAGENT_OPENCLAW_WORKSPACE_DIR"] = workspace_dir
    env["DRUGAGENT_OPENCLAW_SESSION_ID"] = session_id
    env["OPENCLAW_CONFIG_PATH"] = write_local_config(
        openai_base_url=openai_base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        workspace_dir=workspace_dir,
        session_id=session_id,
    )
    return env


def run_agent_local(
    *,
    message: str,
    session_id: str,
    model: str,
    turn: Optional[str] = None,
    label: Optional[str] = None,
    thinking: str = "off",
    timeout_seconds: int = 2000,
) -> OpenClawRun:
    model = _normalize_model_id(model)
    workspace_dir = _session_workspace_dir(session_id)
    model_id = model.split("/", 1)[1] if "/" in model else model
    openai_base_url = oc_credentials.resolve_openai_base_url(model_name=model_id)
    openai_api_key = oc_credentials.resolve_openai_api_key()
    env = _base_env(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        workspace_dir=workspace_dir,
        session_id=session_id,
    )

    verbose_level = os.environ.get("OPENCLAW_AGENT_VERBOSE", "on")
    if _record_builtin_tools_enabled() and verbose_level == "on":
        verbose_level = "full"
    cmd = [
        openclaw_bin(),
        "--log-level",
        os.environ.get("OPENCLAW_LOG_LEVEL", "info"),
        "agent",
        "--local",
        "--json",
        "--session-id",
        session_id,
        "--verbose",
        verbose_level,
        "--thinking",
        thinking,
        "--timeout",
        str(int(timeout_seconds)),
        "-m",
        message,
    ]
    t0 = time.monotonic()
    # NOTE: This is the *outer* call index from our benchmark harness, not OpenClaw's internal tool/step loop.
    turn_s = f" call={turn}" if (turn or "").strip() else ""
    label_s = f" label={label}" if (label or "").strip() else ""
    console_trace: List[str] = []
    start_line = f"[SYS] openclaw start session={session_id} model={model}{turn_s}{label_s}"
    console_trace.append(start_line)
    print(_c(start_line, _DIM), flush=True)
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    out_buf: List[str] = []
    err_buf: List[str] = []
    saw_tool_event = False
    stderr_sys_lines: List[str] = []

    def _drain_stdout():
        assert proc.stdout is not None
        out_buf.append(proc.stdout.read() or "")

    def _drain_stderr():
        nonlocal saw_tool_event
        assert proc.stderr is not None
        for line in proc.stderr:
            err_buf.append(line)
            if os.environ.get("OPENCLAW_STREAM_LOGS", "1") == "1":
                # Map OpenClaw internal tool events to [OBS] (blue), keep other subsystem logs as [SYS] (dim).
                s = (line or "").rstrip("\n")
                if s.startswith("[tools]") or "🛠️" in s:
                    saw_tool_event = True
                    rendered = f"[OBS] {s}"
                    console_trace.append(rendered)
                    print(_c(rendered, _BLUE), flush=True)
                else:
                    # Preserve original content but mark as sys info to avoid confusing with "Observation".
                    stderr_sys_lines.append(s)
                    rendered = f"[SYS] {s}"
                    console_trace.append(rendered)
                    print(_c(rendered, _DIM), flush=True)

    t_out = threading.Thread(target=_drain_stdout, daemon=True)
    t_err = threading.Thread(target=_drain_stderr, daemon=True)
    t_out.start()
    t_err.start()
    rc = proc.wait()
    t_out.join(timeout=1)
    t_err.join(timeout=1)

    dt = time.monotonic() - t0
    end_line = f"[SYS] openclaw end session={session_id} seconds={dt:.2f} code={rc}{turn_s}{label_s}"
    console_trace.append(end_line)
    print(_c(end_line, _DIM), flush=True)
    if os.environ.get("OPENCLAW_STREAM_LOGS", "1") == "1" and not saw_tool_event:
        no_tool_line = "[SYS] no plugin tool Action/Observation events were emitted for this turn"
        console_trace.append(no_tool_line)
        print(_c(no_tool_line, _DIM), flush=True)

    stdout_text = "".join(out_buf)
    stderr_text = "".join(err_buf)
    plugin_tool_events = [
        ln
        for ln in (stderr_text.splitlines() if stderr_text else [])
        if ln.startswith("[tools]") or ("🛠️" in ln)
    ]
    if rc != 0:
        raise RuntimeError((stderr_text or stdout_text).strip() or f"openclaw exited with code {rc}")

    try:
        raw = _extract_json_object(stdout_text)
    except Exception:
        raw = _extract_json_object(stderr_text)
    payloads = raw.get("payloads") or []
    meta = raw.get("meta") or {}
    visible_tools = _visible_tool_names(meta if isinstance(meta, dict) else {})
    visible_builtin_tools, visible_professional_tools = _split_visible_tool_names(visible_tools)
    builtin_tool_events = _extract_builtin_tool_events(stderr_sys_lines, visible_builtin_tools)
    stop_reason = meta.get("stopReason") if isinstance(meta, dict) else None
    pending_tool_calls = meta.get("pendingToolCalls") if isinstance(meta, dict) else None
    observed_builtin_tool_use = bool(builtin_tool_events)
    if isinstance(pending_tool_calls, list):
        for item in pending_tool_calls:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name in visible_builtin_tools:
                observed_builtin_tool_use = True
                break
    if isinstance(stop_reason, str) and stop_reason in {"toolUse", "tool_calls"}:
        observed_builtin_tool_use = True
    text = "\n\n".join([str(x.get("text") or "") for x in payloads if isinstance(x, dict)]).strip()
    if text:
        gen_line = f"[GEN] {text}"
        console_trace.append(gen_line)
    if visible_builtin_tools:
        builtin_visible_line = "[SYS] builtin tools visible: " + ", ".join(visible_builtin_tools)
        console_trace.append(builtin_visible_line)
        print(_c(builtin_visible_line, _DIM), flush=True)
    workspace_line = f"[SYS] workspace_dir={workspace_dir}"
    console_trace.append(workspace_line)
    print(_c(workspace_line, _DIM), flush=True)
    if builtin_tool_events:
        builtin_event_line = f"[SYS] observed builtin tool events: {len(builtin_tool_events)}"
        console_trace.append(builtin_event_line)
        print(_c(builtin_event_line, _DIM), flush=True)
    elif visible_builtin_tools:
        no_builtin_line = "[SYS] no builtin tool events were observed for this turn"
        console_trace.append(no_builtin_line)
        print(_c(no_builtin_line, _DIM), flush=True)
    if isinstance(stop_reason, str) and stop_reason:
        stop_reason_line = f"[SYS] openclaw stopReason={stop_reason}"
        console_trace.append(stop_reason_line)
        print(_c(stop_reason_line, _DIM), flush=True)
    if isinstance(pending_tool_calls, list) and pending_tool_calls:
        pending_names = [str(item.get("name")) for item in pending_tool_calls if isinstance(item, dict) and item.get("name")]
        pending_line = "[SYS] pending tool calls: " + ", ".join(pending_names)
        console_trace.append(pending_line)
        print(_c(pending_line, _DIM), flush=True)
    if os.environ.get("OPENCLAW_PRINT_META", "") == "1":
        print(_c(f"[SYS] openclaw meta_keys={sorted(list(meta.keys()))}", _DIM), flush=True)
        agent_meta = meta.get("agentMeta") if isinstance(meta, dict) else None
        if isinstance(agent_meta, dict):
            print(_c(f"[SYS] openclaw agentMeta_keys={sorted(list(agent_meta.keys()))}", _DIM), flush=True)
    if os.environ.get("OPENCLAW_PRINT_TEXT", "") == "1" and text:
        print(_c(f"[GEN] {text[:300]}", _YELLOW), flush=True)
    return OpenClawRun(
        text=text,
        payloads=payloads,
        meta=meta,
        raw=raw,
        stderr=stderr_text,
        console_trace=console_trace,
        plugin_tool_events=plugin_tool_events,
        builtin_tool_events=builtin_tool_events,
        visible_builtin_tools=visible_builtin_tools,
        visible_professional_tools=visible_professional_tools,
        observed_builtin_tool_use=observed_builtin_tool_use,
    )


