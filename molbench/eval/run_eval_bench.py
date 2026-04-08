"""
Run bench evaluation on an existing results_dir (no agent run).

This script is a deterministic dispatcher based on the provided bench config:
  - Reads dataset + tasks from --cfg
  - Runs the matching evaluator for each task under results_dir/preds/<task>/
  - Writes results_dir/bench_scores.json

No heuristics, no fallback:
  - --cfg is required
  - Unknown dataset/task raises an error
  - Missing preds directory for a configured task raises an error

For Molbench_vs:
    - rank/miss_rank are computed inside evaluate.eval_runner (no separate metric module required)
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _weighted_average(items: list[tuple[float, int]]) -> float:
    total_weight = sum(weight for _, weight in items)
    return sum(value * weight for value, weight in items) / total_weight


def _aggregate_mol_edit_scores(results_out: dict) -> None:
    keys = [key for key in results_out if key.startswith("molbench-mo-edit_") and key != "molbench-mo-edit_overall"]
    if not keys:
        return
    total_n = sum(int(results_out[key]["n_samples"]) for key in keys)
    correct_rate = _weighted_average([(float(results_out[key]["correct_rate"]), int(results_out[key]["n_samples"])) for key in keys])
    valid_rate_items = []
    for key in keys:
        score = results_out[key]
        valid_key = next(metric_key for metric_key in score if metric_key.endswith("-valid-rate"))
        valid_rate_items.append((float(score[valid_key]), int(score["n_samples"])))
    results_out["molbench-mo-edit_overall"] = {
        "correct_rate": correct_rate,
        "valid_rate": _weighted_average(valid_rate_items),
        "n_samples": total_n,
    }


def _aggregate_mol_opt_scores(results_out: dict, prefix: str) -> None:
    keys = [key for key in results_out if key.startswith(prefix + "_") and key != f"{prefix}_overall"]
    keys = [key for key in keys if isinstance(results_out[key].get("improvement"), dict)]
    if not keys:
        return
    total_n = sum(int(results_out[key]["n_samples"]) for key in keys)
    mean_items = [(float(results_out[key]["improvement"]["mean"]), int(results_out[key]["n_samples"])) for key in keys]
    mean = _weighted_average(mean_items)
    second_moment = sum(
        int(results_out[key]["n_samples"]) * (
            float(results_out[key]["improvement"]["variance"]) + float(results_out[key]["improvement"]["mean"]) ** 2
        )
        for key in keys
    ) / total_n
    improvement = {
        "mean": mean,
        "variance": second_moment - mean ** 2,
        "min": min(float(results_out[key]["improvement"]["min"]) for key in keys),
        "max": max(float(results_out[key]["improvement"]["max"]) for key in keys),
        "success_rate": _weighted_average(
            [(float(results_out[key]["improvement"]["success_rate"]), int(results_out[key]["n_samples"])) for key in keys]
        ),
        "best_rate": _weighted_average(
            [(float(results_out[key]["improvement"]["best_rate"]), int(results_out[key]["n_samples"])) for key in keys]
        ),
        "valid_smiles_rate": _weighted_average(
            [(float(results_out[key]["improvement"]["valid_smiles_rate"]), int(results_out[key]["n_samples"])) for key in keys]
        ),
        "valid_score_rate": _weighted_average(
            [(float(results_out[key]["improvement"]["valid_score_rate"]), int(results_out[key]["n_samples"])) for key in keys]
        ),
        "valid_smiles_extract_rate": _weighted_average(
            [(float(results_out[key]["improvement"]["valid_smiles_extract_rate"]), int(results_out[key]["n_samples"])) for key in keys]
        ),
    }
    scaffold = {
        "hard": _weighted_average([(float(results_out[key]["scaffold"]["hard"]), int(results_out[key]["n_samples"])) for key in keys]),
        "soft": _weighted_average([(float(results_out[key]["scaffold"]["soft"]), int(results_out[key]["n_samples"])) for key in keys]),
    }
    results_out[f"{prefix}_overall"] = {
        "improvement": improvement,
        "scaffold": scaffold,
        "n_samples": total_n,
        "Delta": improvement["mean"],
        "SR%": improvement["success_rate"] * 100.0,
    }


def _append_group_overall_scores(results_out: dict) -> None:
    _aggregate_mol_edit_scores(results_out)
    _aggregate_mol_opt_scores(results_out, "molbench-mo-opt")
    _aggregate_mol_opt_scores(results_out, "mol_opt_target")


def _load_cfg(path: str) -> dict:
    try:
        import yaml
    except Exception as e:
        raise RuntimeError(f"PyYAML is required to load config: {e}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a YAML mapping")
    return cfg


def main() -> None:
    ap = argparse.ArgumentParser(description="Run bench eval on existing results_dir (dataset-dispatch).")
    ap.add_argument("results_dir", help="Bench run directory containing preds/ (e.g. .../bench_run_YYYYMMDD_HHMMSS)")
    ap.add_argument("--cfg", required=True, help="The same YAML config used for inference (bench.dataset + bench.tasks).")
    ap.add_argument(
        "--eval-root",
        default=None,
        help="ChemCoTBench baseline_and_eval path (only used when bench.dataset == ChemCoTBench).",
    )
    args = ap.parse_args()

    results_dir = os.path.abspath(args.results_dir)
    if not os.path.isdir(results_dir):
        raise NotADirectoryError(results_dir)

    preds_base = os.path.join(results_dir, "preds")
    if not os.path.isdir(preds_base):
        raise FileNotFoundError(f"Missing preds/ under {results_dir}")

    cfg_path = os.path.abspath(args.cfg)
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(cfg_path)
    cfg = _load_cfg(cfg_path)
    bench_cfg = cfg.get("bench") or {}
    dataset = bench_cfg.get("dataset")
    tasks = bench_cfg.get("tasks")
    if not isinstance(dataset, str) or not dataset.strip():
        raise ValueError("bench.dataset must be a non-empty string")
    if not isinstance(tasks, list) or not tasks or not all(isinstance(x, str) and x.strip() for x in tasks):
        raise ValueError("bench.tasks must be a non-empty list of strings")
    if dataset in ("molbench-ms-3", "Molbench_vs"):
        print("Molbench_vs eval uses GT-top3 average rank logic in evaluate.eval_runner (missing prediction uses candidates_num+1).")

    # Ensure package root is importable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    molbench_root = os.path.dirname(script_dir)
    project_root = os.path.dirname(molbench_root)
    workspace_root = os.path.dirname(project_root)
    for p in (workspace_root, project_root, molbench_root):
        if p not in sys.path:
            sys.path.insert(0, p)

    # Resolve eval_root for ChemCoTBench
    eval_root = ""
    if dataset == "ChemCoTBench":
        work_space = project_root
        if args.eval_root:
            eval_root = os.path.abspath(args.eval_root)
        else:
            p = bench_cfg.get("eval_root")
            if isinstance(p, str) and p.strip():
                eval_root = os.path.abspath(p) if os.path.isabs(p) else os.path.abspath(os.path.join(work_space, p))
            else:
                eval_root = os.path.abspath(os.path.join(work_space, "molbench", "eval", "ChemCoTBench", "baseline_and_eval"))

    from MolClaw.molbench.eval.eval_runner import (
        ChemCoTBenchMolEditEval,
        ChemCoTBenchMolOptPhyschemEval,
        ChemCoTBenchMolOptTargetEval,
        ChemCoTBenchMolOptEval,
        ChemCoTBenchMolUndEval,
        ChemCoTBenchReactionEval,
        ACNetCuratedEval,
        VirtualScreeningCuratedEval,
        MolbenchVsEval,
        RdkitBenchEval,
    )

    results_out: dict = {}

    for task_name in tasks:
        preds_dir = os.path.join(preds_base, task_name)
        if not os.path.isdir(preds_dir):
            raise FileNotFoundError(f"Missing preds dir for configured task: {preds_dir}")

        if dataset == "ChemCoTBench":
            if task_name in ("molbench-mo-edit", "mol_edit"):
                evaluator = ChemCoTBenchMolEditEval()
            elif task_name in ("molbench-mo-opt", "mol_opt_physchem"):
                evaluator = ChemCoTBenchMolOptPhyschemEval()
            elif task_name == "mol_opt_target":
                evaluator = ChemCoTBenchMolOptTargetEval()
            elif task_name == "mol_opt":
                evaluator = ChemCoTBenchMolOptEval()
            elif task_name == "mol_und":
                evaluator = ChemCoTBenchMolUndEval()
            elif task_name == "reaction":
                evaluator = ChemCoTBenchReactionEval()
            else:
                raise ValueError(f"Unsupported task for dataset ChemCoTBench: {task_name}")
        elif dataset in ("molbench-ms-2", "ACNet_curated"):
            if task_name != "acnet_curated":
                raise ValueError(f"Unsupported task for dataset molbench-ms-2: {task_name}")
            evaluator = ACNetCuratedEval()
        elif dataset == "Virtual_Screening_curated":
            if task_name != "virtual_screening_curated":
                raise ValueError(f"Unsupported task for dataset Virtual_Screening_curated: {task_name}")
            evaluator = VirtualScreeningCuratedEval()
        elif dataset in ("molbench-ms-3", "Molbench_vs"):
            if task_name != "molbench_vs":
                raise ValueError(f"Unsupported task for dataset molbench-ms-3: {task_name}")
            evaluator = MolbenchVsEval()
        elif dataset in ("molbench-ms-1", "RDKit_bench"):
            if task_name != "rdkit_bench":
                raise ValueError(f"Unsupported task for dataset molbench-ms-1: {task_name}")
            evaluator = RdkitBenchEval()
        else:
            raise ValueError(f"Unsupported dataset: {dataset}")

        scores = evaluator.run(preds_dir, results_dir, eval_root)
        if scores:
            results_out.update(scores)

    _append_group_overall_scores(results_out)

    out_path = os.path.join(results_dir, "bench_scores.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")
    print("Bench scores:", results_out)


if __name__ == "__main__":
    main()
