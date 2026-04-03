"""
Direct LLM-only bench: same prompts and eval as agent pipeline, no tools.
Usage: python run_baseline.py --cfg config/launch_rdkit_bench.yaml (or other launch_*.yaml)
Output: results/agent_prediction/baseline_run_YYYYMMDD_HHMMSS/ with preds/ and launch cfg; then run run_eval_bench.py.
"""
from __future__ import annotations

import os
import sys
import json
import shutil
import argparse
import traceback
from datetime import datetime
from multiprocessing import Pool

import yaml
from tqdm import tqdm

_script_dir = os.path.dirname(os.path.abspath(__file__))
_pkg_root = os.path.dirname(os.path.dirname(_script_dir))
_work_space = os.path.dirname(_pkg_root)
for _d in (_pkg_root, _work_space):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from openai import OpenAI
from MolClaw.molclaw_run.data_loader.bench_loaders import get_loader, collect_result_text
from MolClaw.molclaw_run.templates.template import ANSWER_OUTPUT_HINT, SYSTEM_PROMPT_MINIMAL
from MolClaw.utils.fix_seed import set_global_seed
from MolClaw.utils.llm_endpoint import resolve_openai_client_kwargs, apply_openai_env


def _resp_to_text(resp) -> str:
    if resp is None:
        return "<none>"
    if hasattr(resp, "model_dump_json"):
        try:
            return resp.model_dump_json(indent=2)
        except Exception:
            pass
    return str(resp)


def _call_llm(prompt: str, system_prompt: str, model: str, seed: int | None, client: OpenAI) -> str:
    messages = [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT_MINIMAL},
        {"role": "user", "content": prompt},
    ]
    params = {"model": model, "messages": messages, "temperature": 0.0}
    if seed is not None:
        params["seed"] = seed
    max_attempts = 3
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            r = client.chat.completions.create(**params)
            choices = getattr(r, "choices", None)
            if not choices:
                raise RuntimeError(
                    f"Empty choices in chat completion response (attempt {attempt}/{max_attempts}). "
                    f"Response: {_resp_to_text(r)[:2000]}"
                )

            msg = getattr(choices[0], "message", None)
            content = getattr(msg, "content", None) if msg is not None else None
            if content is None:
                raise RuntimeError(
                    f"Empty message.content in chat completion response (attempt {attempt}/{max_attempts}). "
                    f"Response: {_resp_to_text(r)[:2000]}"
                )
            if isinstance(content, list):
                # Some providers may return content blocks; join text fields if present.
                text_blocks = []
                for block in content:
                    if isinstance(block, dict):
                        txt = block.get("text")
                        if isinstance(txt, str):
                            text_blocks.append(txt)
                    elif isinstance(block, str):
                        text_blocks.append(block)
                content = "\n".join(text_blocks).strip()
            if not isinstance(content, str):
                content = str(content)
            return content
        except Exception as e:
            last_error = e
            if attempt >= max_attempts:
                raise
    raise RuntimeError(f"LLM call failed after retries: {last_error}")


def _run_one(args):
    task_name, subtask, idx, sample, bench_run_dir, base_dir, cfg = args
    try:
        loader = get_loader(task_name)
        if not loader:
            return (idx, None, f"No loader for task: {task_name}")
        query = loader.get_query(sample, subtask)
        content = loader.get_dataset_content(sample, subtask)
        if content and "#candidates.smi" in query:
            query = query.replace("#candidates.smi", "the following list (one SMILES per line):\n" + content)
        hint = getattr(loader, "get_extra_answer_hint", lambda s, t: None)(sample, subtask) or ANSWER_OUTPUT_HINT
        prompt = query + "\n\n" + hint

        model_cfg = cfg.get("model", {}) or {}
        model = model_cfg.get("llm_model", "gpt-4o")
        seed = cfg.get("settings", {}).get("seed")
        set_global_seed(seed)
        model = apply_openai_env(model, cfg_model=model_cfg) or model
        client_kwargs, _ = resolve_openai_client_kwargs(model, cfg_model=model_cfg)
        client = OpenAI(**client_kwargs)
        reply = _call_llm(prompt, SYSTEM_PROMPT_MINIMAL, model, seed, client)
        result = {"action_history": [{"finish": reply}]}
        raw_text = collect_result_text(result)
        parsed = loader.parse_agent_result(result, subtask)
        entry = loader.build_pred_entry(sample, parsed, raw_text, subtask)
        return (idx, entry, None)
    except Exception as e:
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        return (idx, None, err)


def main():
    parser = argparse.ArgumentParser(description="Run bench with direct LLM (no agent/tools).")
    parser.add_argument("--cfg", required=True, help="Launch YAML (bench.enabled, bench.tasks, bench.data_path, model.llm_model).")
    args = parser.parse_args()

    with open(os.path.abspath(args.cfg), "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    bench_cfg = cfg.get("bench") or {}
    if not bench_cfg.get("enabled"):
        print("bench.enabled is not true; exiting.")
        sys.exit(0)

    base_dir = os.path.abspath(os.path.join(_script_dir, "..", "..", ".."))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bench_run_dir = os.path.join(base_dir, "results", "agent_prediction", f"baseline_run_{ts}")
    os.makedirs(bench_run_dir, exist_ok=True)
    shutil.copy(os.path.abspath(args.cfg), os.path.join(bench_run_dir, os.path.basename(args.cfg)))

    def _abs(p):
        return os.path.abspath(p) if os.path.isabs(p) else os.path.abspath(os.path.join(base_dir, p))

    data_path = bench_cfg.get("data_path")
    task_names = bench_cfg.get("tasks")
    if not data_path or not task_names:
        raise ValueError("bench.data_path and bench.tasks required in config (e.g. launch_rdkit_bench.yaml, launch_chemcot_bench.yaml, launch_acnet_curated_bench.yaml, launch_virtual_screening_curated_bench.yaml).")
    data_path = _abs(data_path)
    max_samples = bench_cfg.get("max_samples_per_subtask")
    max_process = int(bench_cfg.get("max_process") or bench_cfg.get("max_workers") or 1)
    seed = cfg.get("settings", {}).get("seed")
    set_global_seed(seed)

    for task_name in task_names:
        loader = get_loader(task_name)
        if not loader:
            continue
        for subtask in loader.get_subtasks():
            print(f"[Baseline] Start subtask: {task_name}/{subtask}", flush=True)
            samples = loader.load_data(data_path, subtask, max_samples)
            if not samples:
                print(f"[Baseline] Skip subtask (no samples): {task_name}/{subtask}", flush=True)
                continue
            pred_list: list[object | None] = [None] * len(samples)
            errors: list[tuple[int, str]] = []
            if max_process <= 1:
                for idx, sample in enumerate(tqdm(samples, desc=f"{task_name}/{subtask}", leave=True)):
                    _, entry, err = _run_one((task_name, subtask, idx, sample, bench_run_dir, base_dir, cfg))
                    if err:
                        errors.append((idx, err))
                        continue
                    if entry is not None:
                        pred_list[idx] = entry
            else:
                arg_list = [(task_name, subtask, i, s, bench_run_dir, base_dir, cfg) for i, s in enumerate(samples)]
                with Pool(processes=max_process) as pool:
                    for idx, entry, err in tqdm(
                        pool.imap_unordered(_run_one, arg_list),
                        total=len(arg_list),
                        desc=f"{task_name}/{subtask}",
                        leave=True,
                    ):
                        if err:
                            errors.append((idx, err))
                            continue
                        if entry is not None:
                            pred_list[idx] = entry

            if errors:
                first_idx, first_err = errors[0]
                raise RuntimeError(
                    f"Baseline inference failed for {task_name}/{subtask} at sample {first_idx}:\n{first_err}"
                )

            pred_list = [e for e in pred_list if e is not None]
            pred_dir = os.path.join(bench_run_dir, "preds", task_name)
            os.makedirs(pred_dir, exist_ok=True)
            with open(os.path.join(pred_dir, f"{subtask}.json"), "w", encoding="utf-8") as f:
                json.dump(pred_list, f, ensure_ascii=False, indent=2)
            print(f"Wrote preds {task_name}/{subtask} ({len(pred_list)} entries).", flush=True)

    print("RESULTS_DIR=" + os.path.abspath(bench_run_dir), flush=True)


if __name__ == "__main__":
    main()
