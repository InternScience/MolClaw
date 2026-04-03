"""
Run llm_bench datasets with Nanobot agent and write eval-compatible prediction files.

Usage:
  python run_nanobot.py --cfg config/launch_rdkit_bench.yaml --nanobot-mode both
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def tqdm(iterable, **kwargs):  # type: ignore
    try:
        mod = importlib.import_module("tqdm")
        return mod.tqdm(iterable, **kwargs)
    except Exception:
        return iterable


_script_dir = os.path.dirname(os.path.abspath(__file__))
_pkg_root = os.path.dirname(os.path.dirname(_script_dir))
_llm_bench_root = os.path.dirname(_pkg_root)
_workspace_root = os.path.dirname(_llm_bench_root)

for _d in (_pkg_root, _llm_bench_root, _workspace_root):
    if _d not in sys.path:
        sys.path.insert(0, _d)

_nanobot_repo = os.path.join(_workspace_root, "nanobot")
if _nanobot_repo not in sys.path:
    sys.path.insert(0, _nanobot_repo)

from MolClaw.molclaw_run.data_loader.bench_loaders import collect_result_text, get_loader
from MolClaw.molclaw_run.templates.template import ANSWER_OUTPUT_HINT
from MolClaw.utils.fix_seed import set_global_seed


def _load_nanobot_runtime():
    AgentLoop = importlib.import_module("nanobot.agent.loop").AgentLoop
    SkillsLoader = importlib.import_module("nanobot.agent.skills").SkillsLoader
    MessageBus = importlib.import_module("nanobot.bus.queue").MessageBus
    MCPServerConfig = importlib.import_module("nanobot.config.schema").MCPServerConfig
    CustomProvider = importlib.import_module("nanobot.providers.custom_provider").CustomProvider
    SessionManager = importlib.import_module("nanobot.session.manager").SessionManager
    return AgentLoop, SkillsLoader, MessageBus, MCPServerConfig, CustomProvider, SessionManager


NANOBOT_MODES = {"non", "tool", "skills", "both"}
DEFAULT_OPENAI_BASE_URL = ""
DEFAULT_OPENAI_API_KEY = ""
DEFAULT_MCP_URL = "http://127.0.0.1:32208/mcp"


def _normalize_mcp_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return DEFAULT_MCP_URL
    u = u.rstrip("/")
    if u.endswith("/mcp"):
        return u
    return f"{u}/mcp"


def _resolve_cfg_mode(cfg: dict, cli_mode: str | None) -> str:
    if cli_mode:
        mode = cli_mode.strip().lower()
    else:
        mode = (
            cfg.get("settings", {}).get("nanobot_mode")
            or cfg.get("nanobot", {}).get("mode")
            or "both"
        )
        mode = str(mode).strip().lower()
    if mode not in NANOBOT_MODES:
        raise ValueError(f"Invalid nanobot mode: {mode}. Expected one of {sorted(NANOBOT_MODES)}")
    return mode


def _build_prompt(query: str, extra_answer_hint: str | None) -> str:
    prompt = (query or "").strip()
    hint = (extra_answer_hint or ANSWER_OUTPUT_HINT).strip()
    if hint:
        prompt = f"{prompt}\n\n{hint}"
    return prompt


def _copy_tree(src: str, dst: str) -> None:
    if not os.path.isdir(src):
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        src_path = os.path.join(src, name)
        dst_path = os.path.join(dst, name)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dst_path)


def _safe_name(text: str) -> str:
    s = (text or "dataset").strip().lower()
    s = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in s)
    while "__" in s:
        s = s.replace("__", "_")
    s = s.strip("_")
    return s or "dataset"


def _read_session_messages(sample_dir: str) -> list[dict[str, Any]]:
    sessions_dir = os.path.join(sample_dir, "sessions")
    if not os.path.isdir(sessions_dir):
        return []
    files = sorted([f for f in os.listdir(sessions_dir) if f.endswith(".jsonl")])
    if not files:
        return []
    session_path = os.path.join(sessions_dir, files[0])
    msgs: list[dict[str, Any]] = []
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("_type") == "metadata":
                    continue
                if isinstance(data, dict):
                    msgs.append(data)
    except Exception:
        return []
    return msgs


def _to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("text")
                if isinstance(t, str):
                    parts.append(t)
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    try:
        return json.dumps(content, ensure_ascii=False, indent=2)
    except Exception:
        return str(content)


def _write_result_markdown(
    sample_dir: str,
    dataset_name: str,
    question_idx: int,
    mode: str,
    model: str,
    prompt: str,
    result: dict[str, Any],
) -> None:
    messages = _read_session_messages(sample_dir)
    lines: list[str] = []
    lines.append(f"# Nanobot Result - {dataset_name}_{question_idx:04d}")
    lines.append("")
    lines.append(f"- dataset: `{dataset_name}`")
    lines.append(f"- question_idx: `{question_idx}`")
    lines.append(f"- mode: `{mode}`")
    lines.append(f"- model: `{model}`")
    lines.append("")
    lines.append("## User Prompt")
    lines.append("")
    lines.append("```text")
    lines.append(prompt)
    lines.append("```")
    lines.append("")

    lines.append("## Full Reasoning Trace")
    lines.append("")
    if not messages:
        lines.append("No session messages captured.")
    else:
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            lines.append(f"### Step {i} - {role}")
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                lines.append("")
                lines.append("Tool calls:")
                lines.append("```json")
                lines.append(json.dumps(tool_calls, ensure_ascii=False, indent=2))
                lines.append("```")
            content_text = _to_text(msg.get("content"))
            if content_text:
                lines.append("")
                lines.append("```text")
                lines.append(content_text)
                lines.append("```")
            lines.append("")

    lines.append("## Final Result JSON")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    out_path = os.path.join(sample_dir, "result.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _configure_agent_mode(agent: Any, mode: str, mcp_url: str, mcp_api_key: str | None = None) -> None:
    _, _, _, MCPServerConfig, _, _ = _load_nanobot_runtime()
    if mode in ("tool", "both"):
        mcp_url = _normalize_mcp_url(mcp_url)
        headers: dict[str, str] = {}
        if mcp_api_key:
            headers["SCP-HUB-API-KEY"] = mcp_api_key
        agent._mcp_servers = {
            "drug_tools": MCPServerConfig(
                url=mcp_url,
                headers=headers,
                command="",
                args=[],
                env={},
                tool_timeout=0,
            )
        }
    else:
        all_tools = list(agent.tools.tool_names)
        for tool_name in all_tools:
            agent.tools.unregister(tool_name)
        agent._mcp_servers = {}


def _configure_skills_mode(agent: Any, workspace_dir: str, mode: str, skills_src_dir: str) -> None:
    _, SkillsLoader, _, _, _, _ = _load_nanobot_runtime()
    workspace_skills = os.path.join(workspace_dir, "skills")
    if os.path.exists(workspace_skills):
        shutil.rmtree(workspace_skills, ignore_errors=True)

    if mode in ("skills", "both"):
        _copy_tree(skills_src_dir, workspace_skills)
        agent.context.skills = SkillsLoader(Path(workspace_dir), builtin_skills_dir=Path(workspace_skills))
    else:
        # Disable skills entirely (both custom and built-in)
        agent.context.skills = SkillsLoader(Path(workspace_dir), builtin_skills_dir=Path(workspace_dir) / "_empty_skills")


def _run_one_nanobot(args: tuple[Any, ...]) -> tuple[int, dict | None]:
    AgentLoop, _, MessageBus, _, CustomProvider, SessionManager = _load_nanobot_runtime()
    (
        task_name,
        subtask,
        idx,
        sample,
        dataset_name,
        bench_run_dir,
        cfg,
        mode,
        mcp_url,
        mcp_api_key,
        skills_src_dir,
        openai_base_url,
        openai_api_key,
    ) = args

    loader = get_loader(task_name)
    if not loader:
        return idx, None

    settings = cfg.get("settings", {})
    model = cfg.get("model", {}).get("llm_model", "gpt-4o")
    seed = settings.get("seed")
    max_iter = int(settings.get("max_iter", 20))

    sample_dir = os.path.join(bench_run_dir, f"{_safe_name(dataset_name)}_{idx:04d}")
    os.makedirs(sample_dir, exist_ok=True)

    query = loader.get_query(sample, subtask)
    content = loader.get_dataset_content(sample, subtask)
    dataset_path = None
    temp_file_created = False

    if content:
        if task_name == "virtual_screening_curated":
            dataset_path = os.path.join(sample_dir, "candidates.smi")
            with open(dataset_path, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")
        else:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".smi", delete=False) as tf:
                tf.write(content + "\n")
                dataset_path = tf.name
                temp_file_created = True

    extra_answer_hint = getattr(loader, "get_extra_answer_hint", lambda s, t: None)(sample, subtask) or ANSWER_OUTPUT_HINT
    prompt = _build_prompt(query, extra_answer_hint)

    set_global_seed(seed)
    os.environ["LLM_MODEL"] = str(model)

    provider = CustomProvider(
        api_key=openai_api_key,
        api_base=openai_base_url,
        default_model=model,
    )
    bus = MessageBus()
    session_manager = SessionManager(Path(sample_dir))

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=Path(sample_dir),
        model=model,
        max_iterations=max_iter,
        temperature=0.0,
        max_tokens=4096,
        memory_window=100,
        reasoning_effort=settings.get("reasoning_effort"),
        brave_api_key=None,
        web_proxy=None,
        restrict_to_workspace=True,
        session_manager=session_manager,
        mcp_servers={},
        channels_config=None,
    )

    _configure_agent_mode(agent, mode, mcp_url, mcp_api_key)
    _configure_skills_mode(agent, sample_dir, mode, skills_src_dir)

    if dataset_path and os.path.exists(dataset_path):
        target_dataset = os.path.join(sample_dir, os.path.basename(dataset_path))
        if os.path.abspath(target_dataset) != os.path.abspath(dataset_path):
            shutil.copy2(dataset_path, target_dataset)

    async def _run_and_cleanup() -> str:
        try:
            return await agent.process_direct(
                prompt,
                session_key=f"bench:{task_name}:{subtask}:{idx}",
                channel="cli",
                chat_id="bench",
            )
        finally:
            try:
                await agent.close_mcp()
            except Exception:
                pass

            close_funcs = []
            provider_close = getattr(provider, "close", None)
            if callable(provider_close):
                close_funcs.append(provider_close)

            provider_client = getattr(provider, "_client", None)
            if provider_client is not None:
                for name in ("close", "aclose"):
                    fn = getattr(provider_client, name, None)
                    if callable(fn):
                        close_funcs.append(fn)

            called = set()
            for fn in close_funcs:
                key = id(fn)
                if key in called:
                    continue
                called.add(key)
                try:
                    ret = fn()
                    if inspect.isawaitable(ret):
                        await ret
                except Exception:
                    pass

    try:
        response_text = asyncio.run(_run_and_cleanup())
        result = {
            "summary": {
                "user_input": prompt,
                "nanobot_mode": mode,
                "llm_model": model,
            },
            "action_history": [{"finish": response_text}],
            "context": {},
        }
    except asyncio.CancelledError as e:
        result = {
            "summary": {
                "user_input": prompt,
                "nanobot_mode": mode,
                "llm_model": model,
            },
            "error": f"MCP/async cancelled during sample run: {str(e)}",
            "action_history": [],
            "context": {},
        }
    except Exception as e:
        result = {
            "summary": {
                "user_input": prompt,
                "nanobot_mode": mode,
                "llm_model": model,
            },
            "error": str(e),
            "action_history": [],
            "context": {},
        }
    finally:
        if temp_file_created and dataset_path and os.path.exists(dataset_path):
            try:
                os.unlink(dataset_path)
            except Exception:
                pass

    with open(os.path.join(sample_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    _write_result_markdown(
        sample_dir=sample_dir,
        dataset_name=dataset_name,
        question_idx=idx,
        mode=mode,
        model=model,
        prompt=prompt,
        result=result,
    )

    raw_text = collect_result_text(result)
    parsed = loader.parse_agent_result(result, subtask)
    entry = loader.build_pred_entry(sample, parsed, raw_text, subtask)
    return idx, entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Run llm_bench with Nanobot agent.")
    parser.add_argument("--cfg", required=True, help="Launch YAML file path")
    parser.add_argument(
        "--nanobot-mode",
        default=None,
        choices=sorted(NANOBOT_MODES),
        help="Nanobot capability mode: non/tool/skills/both",
    )
    parser.add_argument(
        "--mcp-url",
        default=os.environ.get("NANOBOT_MCP_URL", DEFAULT_MCP_URL),
        help="MCP streamable HTTP URL for drug tools",
    )
    parser.add_argument(
        "--mcp-api-key",
        default=os.environ.get("NANOBOT_MCP_API_KEY", ""),
        help="Optional MCP API key sent as SCP-HUB-API-KEY header",
    )
    args = parser.parse_args()

    cfg_path = os.path.abspath(args.cfg)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    bench_cfg = cfg.get("bench") or {}
    if not bench_cfg.get("enabled"):
        print("bench.enabled is not true; exiting.")
        sys.exit(0)

    mode = _resolve_cfg_mode(cfg, args.nanobot_mode)
    normalized_mcp_url = _normalize_mcp_url(args.mcp_url)
    model = cfg.get("model", {}).get("llm_model", "gpt-4o")
    settings = cfg.get("settings", {})
    seed = settings.get("seed")
    set_global_seed(seed)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bench_run_dir = os.path.join(_llm_bench_root, "results", "agent_prediction", f"nanobot_run_{ts}")
    os.makedirs(bench_run_dir, exist_ok=True)
    shutil.copy2(cfg_path, os.path.join(bench_run_dir, os.path.basename(cfg_path)))

    run_meta = {
        "nanobot_mode": mode,
        "mcp_url": normalized_mcp_url,
        "mcp_api_key_set": bool(args.mcp_api_key),
        "llm_model": model,
        "seed": seed,
    }

    def _abs(p: str) -> str:
        return os.path.abspath(p) if os.path.isabs(p) else os.path.abspath(os.path.join(_llm_bench_root, p))

    data_path = bench_cfg.get("data_path")
    tasks = bench_cfg.get("tasks")
    dataset_name = bench_cfg.get("dataset") or "dataset"
    if not data_path or not tasks:
        raise ValueError("bench.data_path and bench.tasks are required")
    data_path = _abs(data_path)
    max_samples = bench_cfg.get("max_samples_per_subtask")
    configured_max_process = int(bench_cfg.get("max_process") or bench_cfg.get("max_workers") or 1)
    max_process = 1
    if configured_max_process > 1:
        print(
            f"[Nanobot] config requests max_process={configured_max_process}, but this runner enforces sequential execution with max_process=1.",
            flush=True,
        )

    run_meta["configured_max_process"] = configured_max_process
    run_meta["effective_max_process"] = max_process
    with open(os.path.join(bench_run_dir, "nanobot_run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(run_meta, f, ensure_ascii=False, indent=2)

    skills_src_dir = os.path.join(_workspace_root, "skills")
    model_cfg = cfg.get("model", {}) or {}
    openai_base_url = (
        os.environ.get("OPENAI_BASE_URL", "").strip()
        or str(model_cfg.get("base_url") or "").strip()
        or DEFAULT_OPENAI_BASE_URL
    )
    openai_api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or str(model_cfg.get("api_key") or "").strip()
        or DEFAULT_OPENAI_API_KEY
    )
    if not openai_api_key:
        raise ValueError("Missing API key: set OPENAI_API_KEY or model.api_key in config.")

    for task_name in tasks:
        loader = get_loader(task_name)
        if not loader:
            continue
        for subtask in loader.get_subtasks():
            print(f"[Nanobot] Start subtask: {task_name}/{subtask}", flush=True)
            samples = loader.load_data(data_path, subtask, max_samples)
            if not samples:
                print(f"[Nanobot] Skip subtask (no samples): {task_name}/{subtask}", flush=True)
                continue

            pred_list: list[dict | None] = [None] * len(samples)
            arg_list = [
                (
                    task_name,
                    subtask,
                    idx,
                    sample,
                    dataset_name,
                    bench_run_dir,
                    cfg,
                    mode,
                    normalized_mcp_url,
                    args.mcp_api_key,
                    skills_src_dir,
                    openai_base_url,
                    openai_api_key,
                )
                for idx, sample in enumerate(samples)
            ]

            for one_arg in tqdm(arg_list, desc=f"{task_name}/{subtask}", leave=True):
                idx, entry = _run_one_nanobot(one_arg)
                if entry is not None:
                    pred_list[idx] = entry

            pred_list = [x for x in pred_list if x is not None]
            pred_dir = os.path.join(bench_run_dir, "preds", task_name)
            os.makedirs(pred_dir, exist_ok=True)
            pred_path = os.path.join(pred_dir, f"{subtask}.json")
            with open(pred_path, "w", encoding="utf-8") as f:
                json.dump(pred_list, f, ensure_ascii=False, indent=2)
            print(f"[Nanobot] Wrote {pred_path} ({len(pred_list)} entries)", flush=True)

    print("RESULTS_DIR=" + os.path.abspath(bench_run_dir), flush=True)


if __name__ == "__main__":
    main()
