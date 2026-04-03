from __future__ import annotations

import os, shutil
import json
import argparse
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path
import re
import yaml
import traceback
import sys

# Add package root (agent_molecular_universal_official) and shy_local to path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_infer_dir = os.path.dirname(_script_dir)
_agent_root = os.path.dirname(_infer_dir)
_llm_bench_root = os.path.dirname(_agent_root)
for _d in (_agent_root, _llm_bench_root):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from MolClaw.molclaw_run.data_loader.bench_loaders import get_loader, collect_result_text

from MolClaw.utils.fix_seed import set_global_seed
from MolClaw.utils.timing import measure_time, record_timing
from MolClaw.utils.llm_endpoint import apply_openai_env

from MolClaw.molclaw_run.infer.openclaw_agent.openclaw_bridge.openclaw_cli import run_agent_local, OpenClawRun, cleanup_session_artifacts
from MolClaw.molclaw_run.infer.openclaw_agent.openclaw_bridge.skills_prompt import skills_catalog_text
from MolClaw.molclaw_run.infer.openclaw_agent.openclaw_bridge.workspace import workspace_root

ANSWER_OUTPUT_HINT = ""
SKILLS_ONLY_PROMPT = (
    "Skills-only mode is active.\n"
    "You must not reply with a direct final answer before selecting and using the most relevant skill/workflow available in the workspace.\n"
    "On your first step, choose an appropriate skill and follow it; do not answer from prior knowledge alone.\n"
    "If you truly cannot find any relevant skill, explicitly state that no relevant skill is available and only then continue.\n"
)

_RESET = "\033[0m"
_BLUE = "\033[34m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_MAGENTA = "\033[35m"
_BOLD = "\033[1m"


def _c(text: str, color: str) -> str:
    return f"{color}{text}{_RESET}"

def _session_id(task_name: str, subtask: str, idx: int, suffix: str = "") -> str:
    base = f"{task_name}_{subtask}_{idx}"
    return f"{base}_{suffix}".strip("_") if suffix else base


def _pred_id(task_name: str, subtask: str, idx: int) -> str:
    return _session_id(task_name, subtask, idx)


def _sample_id(sample: dict, task_name: str, subtask: str, idx: int) -> str:
    sample_id = sample.get("id") if isinstance(sample, dict) else None
    if sample_id is not None and str(sample_id).strip():
        return str(sample_id).strip()
    return _pred_id(task_name, subtask, idx)


def _bench_session_id(task_name: str, subtask: str, idx: int, bench_run_dir: str) -> str:
    return _session_id(task_name, subtask, idx, suffix=os.path.basename(os.path.abspath(bench_run_dir)))


def _is_truthy_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _skills_only_enabled(settings: dict) -> bool:
    if _is_truthy_flag(settings.get("skills_only_mode")):
        return True
    return _is_truthy_flag(os.environ.get("DRUGAGENT_SKILLS_ONLY"))


def _write_dataset_files(query: str, content: str, workspace_dir: str) -> list[str]:
    names = sorted(set(re.findall(r"#([A-Za-z0-9_.-]+)", query or "")))
    if not names:
        return []
    os.makedirs(workspace_dir, exist_ok=True)
    written: list[str] = []
    for name in names:
        path = os.path.join(workspace_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
        written.append(path)
        hash_path = os.path.join(workspace_dir, f"#{name}")
        if not os.path.exists(hash_path):
            try:
                os.symlink(name, hash_path)
            except (OSError, NotImplementedError):
                with open(hash_path, "w", encoding="utf-8") as f:
                    f.write(content or "")
    return written


def _clear_session_tool_context(workspace_dir: str, session_id: str) -> None:
    path = os.path.join(workspace_dir, ".tool_context", f"{session_id}.json")
    if os.path.isfile(path):
        os.remove(path)


def _sample_done_and_load(out_dir: str, loader, sample, subtask) -> dict | None:
    """If result.json exists, load and return pred entry; else None."""
    traj_path = os.path.join(out_dir, "result.json")
    if not os.path.isfile(traj_path):
        return None
    try:
        with open(traj_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        raw_text = collect_result_text(result)
        parsed = loader.parse_agent_result(result, subtask)
        return loader.build_pred_entry(sample, parsed, raw_text, subtask)
    except Exception:
        return None


def _infer_cfg_path(results_dir: str) -> str:
    candidates = []
    for name in sorted(os.listdir(results_dir)):
        path = os.path.join(results_dir, name)
        if not os.path.isfile(path):
            continue
        if not name.lower().endswith((".yaml", ".yml", ".json")):
            continue
        candidates.append(path)
    if not candidates:
        raise FileNotFoundError(f"no config file found in results_dir: {results_dir}")
    preferred = [p for p in candidates if os.path.basename(p).startswith("launch_")]
    return os.path.abspath(preferred[0] if preferred else candidates[0])


def _resolve_cfg_path(cfg_arg: str | None, results_dir: str | None) -> str:
    if cfg_arg:
        cfg_path = os.path.abspath(cfg_arg)
        if not os.path.isfile(cfg_path):
            raise FileNotFoundError(cfg_path)
        return cfg_path
    if results_dir:
        return _infer_cfg_path(os.path.abspath(results_dir))
    raise ValueError("Either --cfg or --results-dir is required")


def _run_one_sample(args):
    """Run one bench sample (for multiprocessing Pool). Each process creates its own agent, runs one sample, returns (idx, entry)."""
    (task_name, subtask, idx, sample, bench_run_dir, base_dir, cfg, skip_done) = args
    out_dir = os.path.join(bench_run_dir, f"{task_name}_{subtask}_{idx}")
    session_id = _bench_session_id(task_name, subtask, idx, bench_run_dir)
    if skip_done:
        loader = get_loader(task_name)
        if loader:
            entry = _sample_done_and_load(out_dir, loader, sample, subtask)
            if entry is not None:
                return (idx, entry)
    settings = cfg.get("settings", {})
    model_cfg = cfg.get("model", {}) or {}
    llm_model = model_cfg.get("llm_model", "gpt-4o")
    seed = settings.get("seed")
    max_iter = settings.get("max_iter", 20)
    loop_count = settings.get("loop_count", 1)
    enable_manual_input = settings.get("enable_manual_input", 0)
    enable = settings.get("enable", 0)
    summary_max_keys = settings.get("summary_max_keys", 8)
    timeout_seconds = settings.get("timeout_seconds", 10000)
    skills_only_mode = _skills_only_enabled(settings)
    system_prompt = settings.get("system_prompt") or cfg.get("system_prompt") or ""
    set_global_seed(seed)
    llm_model = apply_openai_env(llm_model, cfg_model=model_cfg) or llm_model
    loader = get_loader(task_name)
    if not loader:
        return (idx, None)
    query = loader.get_query(sample, subtask)
    content = loader.get_dataset_content(sample, subtask)
    os.makedirs(out_dir, exist_ok=True)
    extra_answer_hint = loader.get_extra_answer_hint(sample, subtask) or ""
    workspace_dir = str(workspace_root(Path(_agent_root), session_id=session_id))

    try:
        print(_c(f"[SYS] bench {task_name}/{subtask} sample {idx+1} start", _BLUE), flush=True)
        q = (query or "").strip()
        if q:
            head = q[:600] + ("..." if len(q) > 600 else "")
            print(_c(f"[Q] {head}", _BOLD + _MAGENTA), flush=True)
        c = (content or "").strip()
        _clear_session_tool_context(workspace_dir, session_id)
        if c:
            head = c[:300] + ("..." if len(c) > 300 else "")
            print(_c(f"[SYS] dataset_head={head}", _BLUE), flush=True)
        written_files = _write_dataset_files(q, c, workspace_dir)
        if written_files:
            print(_c(f"[SYS] dataset_files_written={written_files}", _BLUE), flush=True)
        model = llm_model or os.environ["LLM_MODEL"]

        task_body = (f"{query}\n").strip()
        call_total = 1
        main_run: OpenClawRun | None = None
        # Bench loaders may provide a required output-format hint (e.g., <answer> wrappers).
        # In bench mode we must inject it here; otherwise parsing/eval may see empty outputs.
        templates_dir = os.path.abspath(os.path.join(_agent_root, "templates"))
        format_prompt_path = os.path.join(templates_dir, "answer_format.md")
        routing_prompt_path = os.path.join(templates_dir, "tool_routing.md")
        variable_routing_prompt_path = os.path.join(templates_dir, "variable_routing.md")
        with open(format_prompt_path, "r", encoding="utf-8") as f:
            format_prompt = f.read().strip()
        with open(routing_prompt_path, "r", encoding="utf-8") as f:
            routing_prompt = f.read().strip()
        with open(variable_routing_prompt_path, "r", encoding="utf-8") as f:
            variable_routing_prompt = f.read().strip()
        parts = []
        if system_prompt:
            parts.append(str(system_prompt).strip())
        if skills_only_mode:
            parts.append(SKILLS_ONLY_PROMPT)
        if routing_prompt:
            parts.append(routing_prompt)
        if variable_routing_prompt:
            parts.append(variable_routing_prompt)
        if format_prompt:
            parts.append(format_prompt)
        if task_body:
            parts.append(str(task_body).strip())
        if extra_answer_hint:
            parts.append(str(extra_answer_hint).strip())
        task = "\n\n".join([p for p in parts if p]) + "\n"
        print(_c("[SYS] mode=native_openclaw_skill_selection", _BLUE), flush=True)

        main_run = run_agent_local(
            message=task,
            session_id=session_id,
            model=model,
            turn=f"1/{call_total}",
            label="main",
            thinking="off",
            timeout_seconds=timeout_seconds,
        )
        answer_text = main_run.text

        result = {
            "action_history": [{"finish": answer_text}],
            "openclaw": {"session_id": session_id},
        }
        result["openclaw"]["model"] = str(model)
        result["openclaw"]["task_body"] = task_body
        result["openclaw"]["task_prompt"] = task
        # Persist tool evidence (if any). OpenClaw tool execution logs are primarily emitted to stderr.
        stderr_text = (main_run.stderr or "") if main_run else ""
        tool_lines = [
            ln
            for ln in (stderr_text.splitlines() if stderr_text else [])
            if ln.startswith("[tools]") or ("🛠️" in ln)
        ]
        result["openclaw"]["used_tools"] = bool(tool_lines)
        result["openclaw"]["tool_events"] = tool_lines[-200:]
        result["openclaw"]["used_plugin_tools"] = bool(getattr(main_run, "plugin_tool_events", []))
        result["openclaw"]["plugin_tool_events"] = list(getattr(main_run, "plugin_tool_events", [])[-200:]) if main_run else []
        result["openclaw"]["used_builtin_tools"] = bool(getattr(main_run, "observed_builtin_tool_use", False))
        result["openclaw"]["builtin_tool_events"] = list(getattr(main_run, "builtin_tool_events", [])[-200:]) if main_run else []
        result["openclaw"]["visible_builtin_tools"] = list(getattr(main_run, "visible_builtin_tools", [])) if main_run else []
        result["openclaw"]["visible_professional_tools"] = list(getattr(main_run, "visible_professional_tools", [])) if main_run else []
        result["openclaw"]["workspace_dir"] = workspace_dir
        result["openclaw"]["stderr_tail"] = stderr_text[-8000:] if stderr_text else ""
        result["openclaw"]["console_trace"] = list(main_run.console_trace[-500:]) if main_run else []
        print(_c(f"[SYS] tool_events_count={len(tool_lines)}", _BLUE), flush=True)
        result["openclaw"]["raw"] = main_run.raw if main_run else {}
        meta = main_run.meta if main_run else {}
        agent_meta = meta.get("agentMeta") if isinstance(meta, dict) else {}
        result["openclaw"]["exec_stats"] = {
            "duration_ms": meta.get("durationMs") if isinstance(meta, dict) else None,
            "aborted": meta.get("aborted") if isinstance(meta, dict) else None,
            "stop_reason": meta.get("stopReason") if isinstance(meta, dict) else None,
            "pending_tool_calls": meta.get("pendingToolCalls") if isinstance(meta, dict) else None,
            "prompt_tokens": agent_meta.get("promptTokens") if isinstance(agent_meta, dict) else None,
            "usage": agent_meta.get("usage") if isinstance(agent_meta, dict) else None,
            "last_call_usage": agent_meta.get("lastCallUsage") if isinstance(agent_meta, dict) else None,
        }
    except Exception as e:
        print(_c(f"[ERR] bench {task_name}/{subtask} sample {idx+1} failed: {e}", _RED), flush=True)
        result = {"error": str(e), "action_history": []}
    raw_text = collect_result_text(result)
    parsed = loader.parse_agent_result(result, subtask)
    entry = loader.build_pred_entry(sample, parsed, raw_text, subtask)
    if entry is not None:
        entry["id"] = _sample_id(sample, task_name, subtask, idx)
        entry["sample_idx"] = idx
    result.setdefault("openclaw", {})
    if isinstance(result["openclaw"], dict):
        result["openclaw"]["workspace_cleanup_planned"] = True
        result["openclaw"]["runtime_cleanup_planned"] = True
    # Save full trajectory to sample dir for analysis
    traj_path = os.path.join(out_dir, "result.json")
    with open(traj_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    cleanup_session_artifacts(session_id)
    return (idx, entry)

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', help='path to launch config (yaml or json)', default=None)
    parser.add_argument('--results-dir', help='existing bench results dir to resume (skip completed samples)', default=None)
    args = parser.parse_args()

    # Load config
    cfg_path = _resolve_cfg_path(args.cfg, args.results_dir)
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    print("CONFIG_PATH=" + cfg_path, flush=True)
    
    base_dir = _llm_bench_root
    settings = cfg.get("settings", {})
    model_cfg = cfg.get("model", {}) or {}
    llm_model = model_cfg.get("llm_model", "gpt-4o")
    seed = settings.get("seed")
    max_iter = settings.get("max_iter", 20)
    loop_count = settings.get("loop_count", 1)
    enable_manual_input = settings.get("enable_manual_input", 0)
    enable = settings.get("enable", 0)
    summary_max_keys = settings.get("summary_max_keys", 8)
    timeout_seconds = settings.get("timeout_seconds", 2000)
    skills_only_mode = _skills_only_enabled(settings)
    system_prompt = settings.get("system_prompt") or cfg.get("system_prompt") or ""
    set_global_seed(seed)
    llm_model = apply_openai_env(llm_model, cfg_model=model_cfg) or llm_model

    if cfg.get("bench", {}).get("enabled"):
        bench_cfg = cfg.get("bench", {})
        def _abs(p):
            return os.path.abspath(p) if os.path.isabs(p) else os.path.abspath(os.path.join(base_dir, p))
        # Use existing results_dir if --results-dir passed (resume mode: skip completed samples)
        resume_dir = args.results_dir
        if resume_dir:
            bench_run_dir = _abs(resume_dir)
            if not os.path.isdir(bench_run_dir):
                raise NotADirectoryError(f"bench.results_dir / --results-dir must exist: {bench_run_dir}")
            skip_done = True
            print(f"[bench] Resume mode: using {bench_run_dir}, skipping completed samples", flush=True)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            bench_run_dir = os.path.join(base_dir, "results", "agent_prediction", f"bench_run_{ts}")
            skip_done = False
        os.makedirs(bench_run_dir, exist_ok=True)
        if not resume_dir:
            shutil.copy(cfg_path, os.path.join(bench_run_dir, os.path.basename(cfg_path)))
        data_path = _abs(bench_cfg.get("data_path") or os.path.join("bench", "ChemCoTBench"))
        task_names = bench_cfg.get("tasks") or ["mol_edit", "mol_opt_physchem", "mol_opt_target"]
        max_samples = bench_cfg.get("max_samples_per_subtask")
        max_process = int(bench_cfg.get("max_process") or bench_cfg.get("max_workers") or 1)
        for task_name in task_names:
            loader = get_loader(task_name)
            if not loader:
                continue
            for subtask in loader.get_subtasks():
                samples = loader.load_data(data_path, subtask, max_samples)
                if not samples:
                    continue
                pred_list = [None] * len(samples)
                if max_process <= 1:
                    for idx, sample in enumerate(samples):
                        out_dir = os.path.join(bench_run_dir, f"{task_name}_{subtask}_{idx}")
                        if skip_done:
                            entry = _sample_done_and_load(out_dir, loader, sample, subtask)
                            if entry is not None:
                                entry["id"] = _sample_id(sample, task_name, subtask, idx)
                                entry["sample_idx"] = idx
                                pred_list[idx] = entry
                                print(f"[bench] {task_name}/{subtask} sample {idx+1}/{len(samples)} skipped (done).", flush=True)
                                continue
                        set_global_seed(seed)
                        try:
                            _, entry = _run_one_sample((task_name, subtask, idx, sample, bench_run_dir, base_dir, cfg, False))
                            pred_list[idx] = entry
                        except Exception as e:
                            pred_list[idx] = None
                            print(f"[bench] {task_name}/{subtask} sample {idx+1}/{len(samples)} failed: {e}", flush=True)
                        if pred_list[idx] is not None:
                            print(f"[bench] {task_name}/{subtask} sample {idx+1}/{len(samples)} done.", flush=True)
                else:
                    arg_list = [
                        (task_name, subtask, idx, sample, bench_run_dir, base_dir, cfg, skip_done)
                        for idx, sample in enumerate(samples)
                    ]
                    with Pool(processes=max_process) as pool:
                        results = pool.map(_run_one_sample, arg_list)
                    for idx, entry in results:
                        if entry is not None:
                            entry["id"] = _sample_id(samples[idx], task_name, subtask, idx)
                            entry["sample_idx"] = idx
                            pred_list[idx] = entry
                        print(f"[bench] {task_name}/{subtask} sample {idx+1}/{len(samples)} done.", flush=True)
                    pred_list = [e for e in pred_list if e is not None]
                pred_dir = os.path.join(bench_run_dir, "preds", task_name)
                os.makedirs(pred_dir, exist_ok=True)
                pred_path = os.path.join(pred_dir, f"{subtask}.json")
                with open(pred_path, "w", encoding="utf-8") as f:
                    json.dump(pred_list, f, ensure_ascii=False, indent=2)
                print(f"[bench] wrote {pred_path}", flush=True)
        # Evaluation is orchestrated by infer/launch_agent.sh using evaluate/run_eval_bench.py (results_dir + cfg).
        print("All results under:", bench_run_dir, flush=True)
        print("RESULTS_DIR=" + os.path.abspath(bench_run_dir), flush=True)
        sys.exit(0)

    # Normal task flow (non-bench)
    print(f"Using LLM model: {llm_model}, seed: {seed}, max_iter: {max_iter}, loop_count: {loop_count}, enable_manual_input: {enable_manual_input}, enable: {enable}")

    # Get data input and user query
    data_config = cfg.get('data', {})
    user_input = cfg.get('query', '') or cfg.get('user_input', '')
    dataset_path = data_config.get('dataset_path') or data_config.get('smiles')
    
    if not user_input:
        raise ValueError("Config must provide query or user_input")
    if not dataset_path:
        raise ValueError("Config must provide data.smiles or data.dataset_path")
    
    dataset_text = ""
    if os.path.exists(dataset_path):
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset_text = f.read().strip()
    else:
        dataset_text = str(dataset_path).strip()
    print(f"Dataset: {os.path.basename(dataset_path) if os.path.exists(dataset_path) else '(inline)'} , Query: {user_input}")

    # Create result dir (so workflow can use it) and write config used for this run
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = _llm_bench_root
    out_dir = os.path.join(base_dir, "results", "agent_prediction", ts)
    os.makedirs(out_dir, exist_ok=True)
    shutil.copy(cfg_path, os.path.join(out_dir, os.path.basename(cfg_path)))
    
    with measure_time("workflow_execution", verbose=True) as timer:
        try:
            model = llm_model or os.environ["LLM_MODEL"]

            dataset_block = f"\n\nDataset content:\n{dataset_text}\n" if dataset_text else ""
            catalog = skills_catalog_text()
            task = (
                f"{system_prompt}\n\n"
                f"{SKILLS_ONLY_PROMPT if skills_only_mode else ''}\n\n"
                f"{catalog}\n\n"
                f"{user_input}\n"
                f"{dataset_block}\n"
                f"{ANSWER_OUTPUT_HINT}\n"
            ).strip()

            answer_text = run_agent_local(
                message=task,
                session_id=f"single:{ts}",
                model=model,
                thinking="off",
                timeout_seconds=timeout_seconds,
            ).text
            result = {
                "action_history": [{"finish": answer_text}],
                "openclaw": {"session_id": f"single:{ts}"},
            }
            result = record_timing(result, timer) if result else result
        except Exception as e:
            result = {
                "user_input": user_input,
                "error": {"error_type": type(e).__name__, "error_message": str(e), "traceback": traceback.format_exc()},
            }
            print(f"\n[ERROR] Workflow execution failed: {e}")

    # Save result
    out_path = os.path.join(out_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved run result to: {os.path.basename(os.path.dirname(out_path))}/{os.path.basename(out_path)}")
    if result.get("error"):
        print(f"[WARNING] Result saved with error information. Check the 'error' field in the JSON file.")

    # agent.reset_context()  # ReinventDrugAgent has no reset_context
    