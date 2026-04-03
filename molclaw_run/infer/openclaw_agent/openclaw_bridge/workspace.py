from __future__ import annotations

import os
import shutil
import fcntl
from pathlib import Path
import sys


def _workspace_session_name(session_id: str | None) -> str:
    raw = (session_id or "").strip()
    if not raw:
        return "default"
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in raw)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "default"


def workspace_root(repo_root: Path, session_id: str | None = None) -> Path:
    env_dir = (os.getenv("DRUGAGENT_OPENCLAW_WORKSPACE_DIR") or "").strip()
    if env_dir:
        return Path(env_dir)
    return repo_root / ".openclaw" / "workspace_session" / _workspace_session_name(session_id)


_MANAGED_MARKER = "This workspace is managed by DrugAgentTools (OpenClaw integration)."
_HERE = Path(__file__).resolve().parents[1]
_NANOBOT_SKILLS_DEFAULT = _HERE.parent.parent / "skills"
_WLL_SKILLS_SRC_DEFAULT = _HERE / "wll_skills"
_SKILLS_SRC_DEFAULT = _HERE / "sxy_skills"


def _python_bin() -> str:
    return (os.getenv("DRUGSDA_PYTHON_BIN") or "").strip() or sys.executable or "python3"


def _repo_root_for_tools(repo_root: Path) -> str:
    return (os.getenv("DRUGAGENT_REPO_ROOT") or "").strip() or str(repo_root.parent.parent.parent)


def _professional_tools_enabled() -> bool:
    raw = os.getenv("DRUGAGENT_ENABLE_PROFESSIONAL_TOOLS")
    if raw is None:
        return True
    value = raw.strip()
    if value not in {"0", "1"}:
        raise ValueError(f"invalid DRUGAGENT_ENABLE_PROFESSIONAL_TOOLS: {value}")
    return value == "1"


def _skills_source_mode() -> str:
    raw_mode = os.getenv("DRUGAGENT_SKILLS_SOURCE_MODE")
    mode = "both" if raw_mode is None else raw_mode.strip().lower()
    if mode in {"", "none"}:
        return ""
    if mode not in {"both", "wll", "sxy"}:
        raise ValueError(f"invalid DRUGAGENT_SKILLS_SOURCE_MODE: {mode}")
    return mode


def _clear_dir_contents(path: Path) -> None:
    if not path.exists():
        return
    for entry in path.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def _runtime_session_dir(repo_root: Path, session_id: str | None = None) -> Path:
    return repo_root / ".openclaw" / "runtime_session" / _workspace_session_name(session_id)


def drugsda_tools_extension_dir(repo_root: Path, session_id: str | None = None) -> Path:
    return _runtime_session_dir(repo_root, session_id=session_id) / "extensions" / "drugsda-tools"


def _skills_source_dirs() -> list[Path]:
    env_root = (os.getenv("DRUGAGENT_SKILLS_ROOT") or "").strip()
    if env_root:
        return [Path(p.strip()) for p in env_root.split(":") if p.strip() and Path(p.strip()).is_dir()]
    if _NANOBOT_SKILLS_DEFAULT.is_dir():
        return [_NANOBOT_SKILLS_DEFAULT]
    mode = _skills_source_mode()
    if not mode:
        return []
    if mode == "wll":
        return [_WLL_SKILLS_SRC_DEFAULT] if _WLL_SKILLS_SRC_DEFAULT.is_dir() else []
    if mode == "sxy":
        return [_SKILLS_SRC_DEFAULT] if _SKILLS_SRC_DEFAULT.is_dir() else []
    return [p for p in (_WLL_SKILLS_SRC_DEFAULT, _SKILLS_SRC_DEFAULT) if p.is_dir()]


def _sync_skills(ws: Path, skills_src_list: list[Path]) -> None:
    skills_dst = ws / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    lock_path = ws / ".skills_sync.lock"
    marker_path = ws / ".skills_root.txt"
    with open(lock_path, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        _clear_dir_contents(skills_dst)
        for skills_src in skills_src_list:
            for entry in sorted(skills_src.iterdir()):
                if not entry.is_dir():
                    continue
                shutil.copytree(entry, skills_dst / entry.name, dirs_exist_ok=True)
        marker_path.write_text("\n".join(str(p) for p in skills_src_list) + "\n", encoding="utf-8")


def _ensure_drugsda_tools_plugin(repo_root: Path, skills_dir: Path, session_id: str | None = None) -> None:
    """
    Create a canonical OpenClaw extension under the OpenClaw home directory.
    This matches the tutorial structure: ~/.openclaw/extensions/<id>/

    In our repo-local layout, ~/.openclaw is mirrored at: <repo_root>/.openclaw/
    and the extension lives at: <repo_root>/.openclaw/extensions/drugsda-tools/
    """
    ext_dir = drugsda_tools_extension_dir(repo_root, session_id=session_id)
    ext_dir.mkdir(parents=True, exist_ok=True)

    # Export FastMCP tool parameter schemas (best-effort) so models pass args reliably.
    try:
        import subprocess

        subprocess.run(
            [
                _python_bin(),
                str(repo_root / "openclaw_tools" / "export_tool_schemas.py"),
                str(ext_dir / "tool_schemas.json"),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ,
                "DRUGAGENT_REPO_ROOT": _repo_root_for_tools(repo_root),
                "DRUGAGENT_OPENCLAW_SKILLS_DIR": str(skills_dir),
            },
        )
        subprocess.run(
            [
                _python_bin(),
                str(repo_root / "openclaw_tools" / "export_tool_descriptions.py"),
                str(ext_dir / "tool_descriptions.json"),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ,
                "DRUGAGENT_REPO_ROOT": _repo_root_for_tools(repo_root),
            },
        )
    except Exception:
        pass

    (ext_dir / "openclaw.plugin.json").write_text(
        (
            "{\n"
            '  "id": "drugsda-tools",\n'
            '  "name": "DrugSDA Tools",\n'
            '  "description": "Expose DrugSDA professional tools as native OpenClaw agent tools (backed by openclaw_tools/run_tool.py).",\n'
            '  "configSchema": {\n'
            '    "type": "object",\n'
            '    "additionalProperties": false,\n'
            '    "properties": {\n'
            '      "pythonBin": { "type": "string", "description": "Python executable to run the tool runner (default: python)." },\n'
            '      "timeoutMs": { "type": "number", "description": "Per-tool timeout in milliseconds (default: 1800000)." }\n'
            "    }\n"
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    (ext_dir / "index.ts").write_text(
        (
            'import path from "node:path";\n'
            'import fs from "node:fs";\n'
            'import { fileURLToPath } from "node:url";\n'
            'import type { AnyAgentTool, OpenClawPluginApi } from "openclaw/plugin-sdk";\n'
            "\n"
            "type PluginCfg = {\n"
            "  pythonBin?: string;\n"
            "  timeoutMs?: number;\n"
            "};\n"
            "\n"
            "function loadSchemas(): Record<string, any> {\n"
            "  try {\n"
            "    const __dirname = path.dirname(fileURLToPath(import.meta.url));\n"
            "    const p = path.join(__dirname, \"tool_schemas.json\");\n"
            "    if (!fs.existsSync(p)) return {};\n"
            "    const raw = fs.readFileSync(p, \"utf-8\");\n"
            "    const parsed = JSON.parse(raw);\n"
            "    return parsed && typeof parsed === \"object\" ? (parsed as any) : {};\n"
            "  } catch {\n"
            "    return {};\n"
            "  }\n"
            "}\n"
            "\n"
            "function loadDescriptions(): Record<string, string> {\n"
            "  try {\n"
            "    const __dirname = path.dirname(fileURLToPath(import.meta.url));\n"
            "    const p = path.join(__dirname, \"tool_descriptions.json\");\n"
            "    if (!fs.existsSync(p)) return {};\n"
            "    const raw = fs.readFileSync(p, \"utf-8\");\n"
            "    const parsed = JSON.parse(raw);\n"
            "    return parsed && typeof parsed === \"object\" ? (parsed as any) : {};\n"
            "  } catch {\n"
            "    return {};\n"
            "  }\n"
            "}\n"
            "\n"
            "const SCHEMAS = loadSchemas();\n"
            "const DESCRIPTIONS = loadDescriptions();\n"
            "\n"
            "function isPlainObject(x: unknown): x is Record<string, unknown> {\n"
            "  return !!x && typeof x === \"object\" && !Array.isArray(x);\n"
            "}\n"
            "\n"
            "function toolNames(): string[] {\n"
            "  return Object.keys(SCHEMAS).sort();\n"
            "}\n"
            "\n"
            "function createRunnerBackedTool(api: OpenClawPluginApi, toolName: string): AnyAgentTool {\n"
            "  const schema = SCHEMAS[toolName];\n"
            "  const desc = DESCRIPTIONS[toolName];\n"
            "  return {\n"
            "    name: toolName,\n"
            "    label: toolName,\n"
            "    description:\n"
            "      (typeof desc === \"string\" && desc.trim()) ||\n"
            "      `DrugSDA tool: ${toolName}. Executes python tool by name via openclaw_tools/run_tool.py and returns JSON result.`,\n"
            "    parameters: schema as any,\n"
            "    async execute(_id: string, params: Record<string, unknown>) {\n"
            "      const pluginCfg = (api.pluginConfig ?? {}) as PluginCfg;\n"
            "      const pythonBin =\n"
            "        (typeof pluginCfg.pythonBin === \"string\" && pluginCfg.pythonBin.trim()) ||\n"
            "        process.env.DRUGSDA_PYTHON_BIN ||\n"
            "        \"python3\";\n"
            "      const timeoutMs =\n"
            "        typeof pluginCfg.timeoutMs === \"number\" && pluginCfg.timeoutMs > 0\n"
            "          ? pluginCfg.timeoutMs\n"
            "          : 30 * 60 * 1000;\n"
            "\n"
            "      const defaults = api.config?.agents?.defaults as unknown as Record<string, unknown> | undefined;\n"
            "      const repoRoot =\n"
            "        (defaults && typeof defaults.repoRoot === \"string\" && defaults.repoRoot.trim()) ||\n"
            "        process.cwd();\n"
            "      const runnerPath = path.join(repoRoot, \"openclaw_tools\", \"run_tool.py\");\n"
            "\n"
            "      const argsObj = isPlainObject(params) ? params : {};\n"
            "      const jsonParams = JSON.stringify(argsObj);\n"
            "\n"
            "      // Emit tool Action/Observation markers to stderr so the host can surface them.\n"
            "      process.stderr.write(`[tools] ${toolName} start args=${jsonParams.slice(0, 800)}\\n`);\n"
            "\n"
            "      const env = { ...process.env };\n"
            "      const shyLocalDir = path.dirname(repoRoot);\n"
            "      const drugAgentRoot = path.dirname(shyLocalDir);\n"
            "      const pyPathParts = [repoRoot, shyLocalDir, drugAgentRoot, env.PYTHONPATH || \"\"].filter(Boolean);\n"
            "      env.PYTHONPATH = pyPathParts.join(\":\");\n"
            "\n"
            "      const cmd = [pythonBin, runnerPath, toolName, jsonParams];\n"
            "      const res = await api.runtime.system.runCommandWithTimeout(cmd, { timeoutMs, cwd: repoRoot, env });\n"
            "\n"
            "      if (res.code !== 0) {\n"
            "        const msg = (res.stderr || res.stdout || \"\").trim();\n"
            "        process.stderr.write(`[tools] ${toolName} error code=${String(res.code)}\\n`);\n"
            "        throw new Error(msg || `Tool ${toolName} failed with code ${String(res.code)}`);\n"
            "      }\n"
            "\n"
            "      const out = (res.stdout || \"\").trim();\n"
            "      let parsed: unknown = out;\n"
            "      try {\n"
            "        parsed = out ? JSON.parse(out) : null;\n"
            "      } catch {\n"
            "        // keep as text\n"
            "      }\n"
            "      const obs = typeof parsed === \"string\" ? parsed : JSON.stringify(parsed);\n"
            "      process.stderr.write(`[tools] ${toolName} obs=${obs.slice(0, 800)}\\n`);\n"
            "      process.stderr.write(`[tools] ${toolName} end ok\\n`);\n"
            "\n"
            "      return {\n"
            "        content: [\n"
            "          {\n"
            "            type: \"text\",\n"
            "            text: typeof parsed === \"string\" ? parsed : JSON.stringify(parsed, null, 2),\n"
            "          },\n"
            "        ],\n"
            "        details: {\n"
            "          tool: toolName,\n"
            "          args: argsObj,\n"
            "          json: parsed,\n"
            "          stdout: res.stdout,\n"
            "          stderr: res.stderr,\n"
            "          code: res.code,\n"
            "        },\n"
            "      };\n"
            "    },\n"
            "  };\n"
            "}\n"
            "\n"
            "export default function register(api: OpenClawPluginApi) {\n"
            "  for (const name of toolNames()) {\n"
            "    api.registerTool(createRunnerBackedTool(api, name) as unknown as AnyAgentTool);\n"
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )


def ensure_workspace(repo_root: Path, session_id: str | None = None) -> Path:
    (repo_root / ".openclaw" / "credentials").mkdir(parents=True, exist_ok=True)
    (repo_root / ".openclaw" / "agents").mkdir(parents=True, exist_ok=True)
    ws = workspace_root(repo_root, session_id=session_id)
    (ws / "skills").mkdir(parents=True, exist_ok=True)
    skills_src_list = _skills_source_dirs()
    _sync_skills(ws, skills_src_list)
    if _professional_tools_enabled():
        _ensure_drugsda_tools_plugin(repo_root, ws / "skills", session_id=session_id)
    else:
        ext_dir = drugsda_tools_extension_dir(repo_root, session_id=session_id)
        if ext_dir.exists():
            shutil.rmtree(ext_dir)

    agents_path = ws / "AGENTS.md"
    if not agents_path.exists():
        agents_path.write_text(_MANAGED_MARKER + "\n", encoding="utf-8")

    soul_path = ws / "SOUL.md"
    if not soul_path.exists():
        soul_path.write_text(
            "You are an agent running under OpenClaw.\n"
            "Use available tools when needed; never claim you executed code unless you actually ran a tool.\n",
            encoding="utf-8",
        )

    tools_path = ws / "TOOLS.md"
    if _professional_tools_enabled():
        try:
            import subprocess

            gen_script = repo_root / "openclaw_tools" / "generate_tools_md.py"
            if gen_script.is_file():
                res = subprocess.run(
                    [
                        _python_bin(),
                        str(gen_script),
                        str(tools_path),
                    ],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env={
                        **os.environ,
                        "DRUGAGENT_REPO_ROOT": _repo_root_for_tools(repo_root),
                    },
                )
                if res.returncode != 0:
                    raise RuntimeError("generate_tools_md failed")
        except Exception:
            # Keep existing TOOLS.md if generation fails.
            pass
    elif tools_path.exists():
        tools_path.unlink()

    marker = ws / ".skills_root.txt"
    marker.write_text("\n".join(str(p) for p in skills_src_list) + "\n", encoding="utf-8")
    return ws


