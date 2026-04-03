"""
Run llm_bench datasets with Claude CLI and write eval-compatible prediction files.

Usage:
  python run_claude.py --cfg config/launch_rdkit_bench.yaml --claude-mode both
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Any

import yaml


def tqdm(iterable, **kwargs):  # type: ignore
    try:
        import importlib

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

from MolClaw.molclaw_run.data_loader.bench_loaders import collect_result_text, get_loader
from MolClaw.molclaw_run.templates.template import ANSWER_OUTPUT_HINT
from MolClaw.utils.fix_seed import set_global_seed

CLAUDE_MODES = {"non", "both"}


def _resolve_cfg_mode(cfg: dict, cli_mode: str | None) -> str:
    if cli_mode:
        mode = cli_mode.strip().lower()
    else:
        mode = (
            cfg.get("settings", {}).get("claude_mode")
            or cfg.get("settings", {}).get("nanobot_mode")
            or "both"
        )
        mode = str(mode).strip().lower()
    if mode not in CLAUDE_MODES:
        raise ValueError(f"Invalid claude mode: {mode}. Expected one of {sorted(CLAUDE_MODES)}")
    return mode


def _safe_name(text: str) -> str:
    s = (text or "dataset").strip().lower()
    s = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in s)
    while "__" in s:
        s = s.replace("__", "_")
    s = s.strip("_")
    return s or "dataset"


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


def _build_prompt(query: str, answer_hint: str, mode: str, input_file: str | None) -> str:
    lines: list[str] = []
    lines.append((query or "").strip())
    lines.append("")
    lines.append((answer_hint or ANSWER_OUTPUT_HINT).strip())
    lines.append("")
    lines.append("Execution constraints:")
    lines.append("1. You are already in the per-sample workspace directory. Do not access, read, or search for any files outside of this current directory.")
    lines.append("2. Put final answer inside <answer>...</answer> for evaluator parsing.")
    lines.append("3. Save process notes, skills you used and key outputs to result.md in current directory.")
    # if input_file:
    #     lines.append(f"4. Input data file is available at ./{input_file}.")
    if mode == "both":
        lines.append("Skills are available under ./.claude/skills; use them when needed.")
    return "\n".join(lines).strip() + "\n"


def _read_text_if_exists(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _contains_answer_tag(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return "<answer>" in low and "</answer>" in low


def _pick_primary_text(stdout: str, result_md: str, stderr: str) -> str:
    for candidate in (stdout, result_md, stderr):
        if _contains_answer_tag(candidate):
            return candidate
    for candidate in (stdout, result_md, stderr):
        if candidate and candidate.strip():
            return candidate
    return ""


def _run_claude_cli(
    sample_dir: str,
    prompt: str,
    claude_bin: str,
    llm_model: str,
    extra_args: list[str],
) -> dict[str, Any]:
    base_cmd = [claude_bin, "--dangerously-skip-permissions", "-p"] + list(extra_args)

    def _exec(command: list[str]) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                cwd=sample_dir,
                check=False,
            )
            return {
                "return_code": int(proc.returncode),
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "command": command,
            }
        except FileNotFoundError:
            return {
                "return_code": 127,
                "stdout": "",
                "stderr": f"Claude CLI not found: {claude_bin}",
                "command": command,
            }
        except Exception as e:
            return {
                "return_code": 1,
                "stdout": "",
                "stderr": str(e),
                "command": command,
            }

    tried_with_model = False
    res: dict[str, Any]
    if llm_model:
        tried_with_model = True
        cmd_with_model = base_cmd + ["--model", llm_model]
        res = _exec(cmd_with_model)
        err_text = (res.get("stderr") or "").lower()
        unknown_model_flag = (
            "unknown option" in err_text
            or "unrecognized option" in err_text
            or "unexpected argument '--model'" in err_text
        )
        if unknown_model_flag:
            res = _exec(base_cmd)
            res["model_flag_fallback"] = True
        else:
            res["model_flag_fallback"] = False
    else:
        res = _exec(base_cmd)
        res["model_flag_fallback"] = False

    res["tried_with_model"] = tried_with_model
    return res


def _write_runner_markdown(
    sample_dir: str,
    dataset_name: str,
    question_idx: int,
    subtask: str,
    mode: str,
    model: str,
    prompt: str,
    cli_result: dict[str, Any],
    external_result_md: str,
    primary_text: str,
) -> None:
    out_path = os.path.join(sample_dir, "result.md")
    lines: list[str] = []
    lines.append(f"# Claude Result - {dataset_name}_{question_idx:04d}")
    lines.append("")
    lines.append(f"- dataset: `{dataset_name}`")
    lines.append(f"- subtask: `{subtask}`")
    lines.append(f"- question_idx: `{question_idx}`")
    lines.append(f"- mode: `{mode}`")
    lines.append(f"- model: `{model}`")
    lines.append(f"- return_code: `{cli_result.get('return_code')}`")
    lines.append("")

    lines.append("## Prompt")
    lines.append("")
    lines.append("```text")
    lines.append(prompt.rstrip())
    lines.append("```")
    lines.append("")

    lines.append("## CLI Command")
    lines.append("")
    cmd = cli_result.get("command") or []
    lines.append("```bash")
    lines.append(" ".join(shlex.quote(str(x)) for x in cmd))
    lines.append("```")
    lines.append("")

    lines.append("## Primary Text Used For Parsing")
    lines.append("")
    lines.append("```text")
    lines.append((primary_text or "").strip())
    lines.append("```")
    lines.append("")

    stdout = (cli_result.get("stdout") or "").strip()
    stderr = (cli_result.get("stderr") or "").strip()

    lines.append("## CLI STDOUT")
    lines.append("")
    lines.append("```text")
    lines.append(stdout)
    lines.append("```")
    lines.append("")

    lines.append("## CLI STDERR")
    lines.append("")
    lines.append("```text")
    lines.append(stderr)
    lines.append("```")
    lines.append("")

    if external_result_md.strip():
        lines.append("## Claude Generated result.md (Original)")
        lines.append("")
        lines.append("```text")
        lines.append(external_result_md.rstrip())
        lines.append("```")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _run_one_claude(args: tuple[Any, ...]) -> tuple[int, dict | None]:
    (
        task_name,
        subtask,
        idx,
        sample,
        dataset_name,
        bench_run_dir,
        cfg,
        mode,
        claude_bin,
        extra_args,
        skills_src_dir,
    ) = args

    loader = get_loader(task_name)
    if not loader:
        return idx, None

    settings = cfg.get("settings", {})
    model = cfg.get("model", {}).get("llm_model", "")
    seed = settings.get("seed")

    sample_dir = os.path.join(bench_run_dir, f"{_safe_name(dataset_name)}_{idx:04d}")
    os.makedirs(sample_dir, exist_ok=True)

    query = loader.get_query(sample, subtask)
    content = loader.get_dataset_content(sample, subtask)
    input_filename: str | None = None
    if content:
        input_filename = "candidates.smi" if task_name == "virtual_screening_curated" else "input.smi"
        input_path = os.path.join(sample_dir, input_filename)
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")

    claude_skills_dir = os.path.join(sample_dir, ".claude", "skills")
    if os.path.exists(claude_skills_dir):
        shutil.rmtree(claude_skills_dir, ignore_errors=True)
    if mode == "both":
        _copy_tree(skills_src_dir, claude_skills_dir)

    extra_answer_hint = getattr(loader, "get_extra_answer_hint", lambda s, t: None)(sample, subtask) or ANSWER_OUTPUT_HINT
    prompt = _build_prompt(query, extra_answer_hint, mode, input_filename)

    set_global_seed(seed)
    cli_result = _run_claude_cli(
        sample_dir=sample_dir,
        prompt=prompt,
        claude_bin=claude_bin,
        llm_model=str(model or ""),
        extra_args=extra_args,
    )

    claude_result_md_path = os.path.join(sample_dir, "result.md")
    external_result_md = _read_text_if_exists(claude_result_md_path)
    if external_result_md:
        try:
            with open(os.path.join(sample_dir, "claude_result.md"), "w", encoding="utf-8") as f:
                f.write(external_result_md)
        except Exception:
            pass

    stdout = cli_result.get("stdout") or ""
    stderr = cli_result.get("stderr") or ""
    primary_text = _pick_primary_text(stdout, external_result_md, stderr)

    result: dict[str, Any] = {
        "summary": {
            "user_input": prompt,
            "claude_mode": mode,
            "llm_model": model,
            "return_code": cli_result.get("return_code"),
        },
        "action_history": [{"finish": primary_text}],
        "context": {
            "stdout": stdout,
            "stderr": stderr,
            "command": cli_result.get("command", []),
            "tried_with_model": cli_result.get("tried_with_model", False),
            "model_flag_fallback": cli_result.get("model_flag_fallback", False),
        },
    }

    if int(cli_result.get("return_code", 1)) != 0:
        result["error"] = f"Claude CLI failed with return code {cli_result.get('return_code')}"

    with open(os.path.join(sample_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    _write_runner_markdown(
        sample_dir=sample_dir,
        dataset_name=dataset_name,
        question_idx=idx,
        subtask=subtask,
        mode=mode,
        model=str(model),
        prompt=prompt,
        cli_result=cli_result,
        external_result_md=external_result_md,
        primary_text=primary_text,
    )

    raw_text = collect_result_text(result)
    parsed = loader.parse_agent_result(result, subtask)
    entry = loader.build_pred_entry(sample, parsed, raw_text, subtask)
    return idx, entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Run llm_bench with Claude CLI.")
    parser.add_argument("--cfg", required=True, help="Launch YAML file path")
    parser.add_argument(
        "--claude-mode",
        default=None,
        choices=sorted(CLAUDE_MODES),
        help="Claude capability mode: non|both",
    )
    parser.add_argument(
        "--claude-bin",
        default=os.environ.get("CLAUDE_BIN", "claude"),
        help="Claude CLI executable name or path",
    )
    parser.add_argument(
        "--claude-extra-args",
        nargs="*",
        default=None,
        help="Additional CLI args appended to claude command",
    )
    args = parser.parse_args()

    cfg_path = os.path.abspath(args.cfg)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    bench_cfg = cfg.get("bench") or {}
    if not bench_cfg.get("enabled"):
        print("bench.enabled is not true; exiting.")
        sys.exit(0)

    mode = _resolve_cfg_mode(cfg, args.claude_mode)
    settings = cfg.get("settings", {})
    extra_args = list(args.claude_extra_args or settings.get("claude_extra_args") or [])
    model = cfg.get("model", {}).get("llm_model", "")
    seed = settings.get("seed")
    set_global_seed(seed)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bench_run_dir = os.path.join(_llm_bench_root, "results", "agent_prediction", f"claude_run_{ts}")
    os.makedirs(bench_run_dir, exist_ok=True)
    shutil.copy2(cfg_path, os.path.join(bench_run_dir, os.path.basename(cfg_path)))

    run_meta = {
        "claude_mode": mode,
        "claude_bin": args.claude_bin,
        "claude_extra_args": extra_args,
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
            f"[Claude] config requests max_process={configured_max_process}, but this runner enforces sequential execution with max_process=1.",
            flush=True,
        )
    run_meta["configured_max_process"] = configured_max_process
    run_meta["effective_max_process"] = max_process
    with open(os.path.join(bench_run_dir, "claude_run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(run_meta, f, ensure_ascii=False, indent=2)

    skills_src_dir = os.path.join(_workspace_root, "skills")

    for task_name in tasks:
        loader = get_loader(task_name)
        if not loader:
            continue

        for subtask in loader.get_subtasks():
            print(f"[Claude] Start subtask: {task_name}/{subtask}", flush=True)
            samples = loader.load_data(data_path, subtask, max_samples)
            if not samples:
                print(f"[Claude] Skip subtask (no samples): {task_name}/{subtask}", flush=True)
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
                    args.claude_bin,
                    extra_args,
                    skills_src_dir,
                )
                for idx, sample in enumerate(samples)
            ]

            for one_arg in tqdm(arg_list, desc=f"{task_name}/{subtask}", leave=True):
                idx, entry = _run_one_claude(one_arg)
                if entry is not None:
                    pred_list[idx] = entry

            pred_list = [x for x in pred_list if x is not None]
            pred_dir = os.path.join(bench_run_dir, "preds", task_name)
            os.makedirs(pred_dir, exist_ok=True)
            pred_path = os.path.join(pred_dir, f"{subtask}.json")
            with open(pred_path, "w", encoding="utf-8") as f:
                json.dump(pred_list, f, ensure_ascii=False, indent=2)
            print(f"[Claude] Wrote {pred_path} ({len(pred_list)} entries)", flush=True)

    print("RESULTS_DIR=" + os.path.abspath(bench_run_dir), flush=True)


if __name__ == "__main__":
    main()
