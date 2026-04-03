"""
Run Biomni in llm_bench bench mode.

Output layout is aligned with other runners:
  results/agent_prediction/biomni_run_YYYYMMDD_HHMMSS/preds/<task>/<subtask>.json
"""

from __future__ import annotations

import argparse
import importlib
import json
import multiprocessing as mp
import os
import shutil
import sys
import tempfile
from datetime import datetime
from typing import Any

import yaml

_script_dir = os.path.dirname(os.path.abspath(__file__))
_pkg_root = os.path.dirname(os.path.dirname(_script_dir))
_work_space = os.path.dirname(_pkg_root)
for _d in (_pkg_root, _work_space):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from MolClaw.molclaw_run.data_loader.bench_loaders import collect_result_text, get_loader
from MolClaw.molclaw_run.templates.template import ANSWER_OUTPUT_HINT


INFRA_FAILURE_PATTERNS = [
    "rpc_client.h:203",
    "failed to connect to gcs within 60 seconds",
    "gcs may have been killed",
    "the program will terminate",
]


def _resolve_path(base_dir: str, p: str | None, default_rel: str | None = None) -> str:
    if isinstance(p, str) and p.strip():
        path = p.strip()
    elif default_rel is not None:
        path = default_rel
    else:
        raise ValueError("Path is required")
    return os.path.abspath(path) if os.path.isabs(path) else os.path.abspath(os.path.join(base_dir, path))


def _extract_final_text(resp: Any) -> str:
    # A1.go returns (self.log, message.content)
    if isinstance(resp, tuple) and len(resp) >= 2:
        if isinstance(resp[1], str):
            return resp[1]
        return str(resp[1])
    if isinstance(resp, list) and len(resp) >= 2 and isinstance(resp[1], str):
        return resp[1]
    if isinstance(resp, str):
        return resp
    return ""


def _is_infra_failure_text(text: str | None) -> bool:
    if not text or not isinstance(text, str):
        return False
    lowered = text.lower()
    return any(pattern in lowered for pattern in INFRA_FAILURE_PATTERNS)


def _child_run_biomni_go(payload: dict[str, Any], out_q: mp.Queue) -> None:
    """Run one Biomni sample in child process to isolate hard crashes (e.g., Ray/GCS abort)."""
    try:
        # Some Biomni internal paths still read OPENAI_* directly; mirror cfg values into env in child.
        if payload.get("api_key"):
            os.environ["OPENAI_API_KEY"] = str(payload.get("api_key"))
        if payload.get("base_url"):
            os.environ["OPENAI_BASE_URL"] = str(payload.get("base_url"))

        biomni_repo_path = payload["biomni_repo_path"]
        if biomni_repo_path not in sys.path:
            sys.path.insert(0, biomni_repo_path)

        biomni_agent_module = importlib.import_module("biomni.agent")
        A1 = getattr(biomni_agent_module, "A1")

        agent = A1(
            path=payload["data_root"],
            llm=payload.get("llm_model"),
            source=payload.get("source"),
            use_tool_retriever=payload.get("use_tool_retriever"),
            timeout_seconds=payload.get("timeout_seconds"),
            base_url=payload.get("base_url"),
            api_key=payload.get("api_key"),
            commercial_mode=payload.get("commercial_mode"),
            **({"expected_data_lake_files": payload.get("expected_data_lake_files")} if payload.get("expected_data_lake_files") is not None else {})
        )

        response = agent.go(payload["prompt"])
        final_text = _extract_final_text(response)
        out_q.put({"ok": True, "final_text": final_text})
    except BaseException as e:  # noqa: BLE001
        out_q.put({"ok": False, "error": str(e)})


def _run_sample_isolated(payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    """Execute one sample in isolated child process and return result dict.

    Returns keys:
      - ok: bool
      - final_text: str (when ok)
      - error: str (when not ok)
    """
    ctx = mp.get_context("spawn")
    out_q: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_child_run_biomni_go, args=(payload, out_q), daemon=True)
    proc.start()
    proc.join(timeout_seconds)

    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        return {"ok": False, "error": f"InfraFailure: child timeout after {timeout_seconds}s"}

    # Hard crash / fatal exit in child (e.g., Ray abort) usually yields non-zero exit code.
    if proc.exitcode != 0:
        return {"ok": False, "error": f"InfraFailure: child process exited with code {proc.exitcode}"}

    if out_q.empty():
        return {"ok": False, "error": "InfraFailure: child finished without returning result"}

    return out_q.get()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Biomni on llm_bench bench tasks.")
    parser.add_argument("--cfg", required=True, help="path to launch config (yaml/json)")
    args = parser.parse_args()

    cfg_path = os.path.abspath(args.cfg)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    bench_cfg = cfg.get("bench") or {}
    if not bench_cfg.get("enabled"):
        raise ValueError("bench.enabled must be true for run_biomni.py")

    tasks = bench_cfg.get("tasks") or []
    if not tasks:
        raise ValueError("bench.tasks must be non-empty")

    biomni_cfg = cfg.get("biomni") or {}
    biomni_repo_path = _resolve_path(_work_space, biomni_cfg.get("repo_path"), default_rel=os.path.join("..", "Biomni"))
    if not os.path.isdir(biomni_repo_path):
        raise FileNotFoundError(f"Biomni repo path not found: {biomni_repo_path}")
    if biomni_repo_path not in sys.path:
        sys.path.insert(0, biomni_repo_path)

    biomni_agent_module = importlib.import_module("biomni.agent")
    A1 = getattr(biomni_agent_module, "A1")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bench_run_dir = os.path.join(_work_space, "results", "agent_prediction", f"biomni_run_{ts}")
    os.makedirs(bench_run_dir, exist_ok=True)
    shutil.copy(cfg_path, os.path.join(bench_run_dir, os.path.basename(cfg_path)))

    data_path = _resolve_path(_work_space, bench_cfg.get("data_path"), default_rel=os.path.join("bench", "ChemCoTBench"))
    max_samples = bench_cfg.get("max_samples_per_subtask")

    llm_model = cfg.get("model", {}).get("llm_model", "gpt-4o")
    source = biomni_cfg.get("source")
    timeout_seconds = biomni_cfg.get("timeout_seconds")
    base_url = biomni_cfg.get("base_url")
    api_key = biomni_cfg.get("api_key")
    commercial_mode = biomni_cfg.get("commercial_mode")
    use_tool_retriever = biomni_cfg.get("use_tool_retriever")

    # Biomni defaults to OpenAI-style client when source/api_key are not explicitly configured.
    # Fail fast to avoid generating a full run of empty predictions caused by missing credentials.
    if not api_key and not os.environ.get("OPENAI_API_KEY"):
        raise ValueError(
            "Missing API credentials for Biomni run: set biomni.api_key in cfg or export OPENAI_API_KEY before running."
        )

    # Biomni auto-detect picks OpenAI for gpt-* models before checking base_url,
    # which can ignore cfg api_key/base_url in some internal paths.
    # If custom endpoint is provided but source omitted, force Custom route.
    if source is None and base_url:
        source = "Custom"

    # Mirror credentials to process env so all downstream clients (including tool internals)
    # can read OPENAI_* consistently.
    if api_key:
        os.environ["OPENAI_API_KEY"] = str(api_key)
    if base_url:
        os.environ["OPENAI_BASE_URL"] = str(base_url)

    data_root = _resolve_path(biomni_repo_path, biomni_cfg.get("path"), default_rel="data")
    expected_data_lake_files = biomni_cfg.get("expected_data_lake_files")

    isolate_sample_process = bool(biomni_cfg.get("isolate_sample_process", True))
    sample_timeout_seconds = int(biomni_cfg.get("sample_timeout_seconds", 1800))

    agent = None
    if not isolate_sample_process:
        print(f"[biomni] init shared A1 with llm={llm_model}, source={source}, data_root={data_root}", flush=True)
        agent = A1(
            path=data_root,
            llm=llm_model,
            source=source,
            use_tool_retriever=use_tool_retriever,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
            api_key=api_key,
            commercial_mode=commercial_mode,
            **({"expected_data_lake_files": expected_data_lake_files} if expected_data_lake_files is not None else {})
        )
    else:
        print(
            f"[biomni] per-sample isolated mode enabled, llm={llm_model}, source={source}, data_root={data_root}, timeout={sample_timeout_seconds}s",
            flush=True,
        )

    for task_name in tasks:
        loader = get_loader(task_name)
        if not loader:
            print(f"[biomni] skip unsupported task: {task_name}", flush=True)
            continue

        for subtask in loader.get_subtasks():
            samples = loader.load_data(data_path, subtask, max_samples)
            if not samples:
                print(f"[biomni] skip empty subtask: {task_name}/{subtask}", flush=True)
                continue

            pred_list: list[dict[str, Any]] = []
            for idx, sample in enumerate(samples):
                query = loader.get_query(sample, subtask)
                content = loader.get_dataset_content(sample, subtask)
                out_dir = os.path.join(bench_run_dir, f"{task_name}_{subtask}_{idx}")
                os.makedirs(out_dir, exist_ok=True)

                # Keep compatibility with existing runner behavior: optionally write dataset content,
                # but Biomni currently consumes only query; this file is for traceability.
                ds_path = None
                if content:
                    if task_name == "virtual_screening_curated":
                        ds_path = os.path.join(out_dir, "candidates.smi")
                        with open(ds_path, "w", encoding="utf-8") as f:
                            f.write(content.strip() + "\n")
                    else:
                        with tempfile.NamedTemporaryFile(mode="w", suffix=".smi", delete=False) as tf:
                            tf.write(content + "\n")
                            ds_path = tf.name

                error = None
                response = None
                final_text = ""
                infra_failure_raw_text = ""
                extra_answer_hint = getattr(loader, "get_extra_answer_hint", lambda s, t: None)(sample, subtask) or ANSWER_OUTPUT_HINT
                prompt = query + "\n\n" + extra_answer_hint
                try:
                    if isolate_sample_process:
                        child_payload = {
                            "biomni_repo_path": biomni_repo_path,
                            "data_root": data_root,
                            "llm_model": llm_model,
                            "source": source,
                            "use_tool_retriever": use_tool_retriever,
                            "timeout_seconds": timeout_seconds,
                            "base_url": base_url,
                            "api_key": api_key,
                            "commercial_mode": commercial_mode,
                            "expected_data_lake_files": expected_data_lake_files,
                            "prompt": prompt,
                        }
                        child_result = _run_sample_isolated(child_payload, sample_timeout_seconds)
                        if child_result.get("ok"):
                            final_text = str(child_result.get("final_text") or "")
                        else:
                            error = str(child_result.get("error") or "InfraFailure: unknown child failure")
                            final_text = ""
                    else:
                        assert agent is not None
                        response = agent.go(prompt)
                        final_text = _extract_final_text(response)
                except KeyboardInterrupt:
                    raise
                except BaseException as e:  # noqa: BLE001
                    error = str(e)
                finally:
                    if ds_path and os.path.exists(ds_path) and task_name != "virtual_screening_curated":
                        try:
                            os.unlink(ds_path)
                        except OSError:
                            pass

                if _is_infra_failure_text(error) or _is_infra_failure_text(final_text):
                    infra_failure_raw_text = final_text
                    error = (
                        "InfraFailure: detected Ray/GCS failure while processing this sample; "
                        "marked as failed and continued to next sample."
                    )
                    response = None
                    final_text = ""

                run_result = {
                    "action_history": [{"finish": final_text}],
                    "error": error,
                    "biomni_response": response,
                }
                if infra_failure_raw_text:
                    run_result["infra_failure_raw_text"] = infra_failure_raw_text
                raw_text = collect_result_text(run_result)
                parsed = loader.parse_agent_result(run_result, subtask)
                entry = loader.build_pred_entry(sample, parsed, raw_text, subtask)
                if error:
                    entry["biomni_error"] = error
                if infra_failure_raw_text:
                    entry["infra_failure_raw_text"] = infra_failure_raw_text[:4000]
                if isinstance(sample, dict) and sample.get("id") is not None:
                    entry["id"] = sample.get("id")
                pred_list.append(entry)

                traj_path = os.path.join(out_dir, "result.json")
                with open(traj_path, "w", encoding="utf-8") as f:
                    json.dump(run_result, f, ensure_ascii=False, indent=2)

                print(f"[biomni] {task_name}/{subtask} sample {idx + 1}/{len(samples)} done", flush=True)

            pred_dir = os.path.join(bench_run_dir, "preds", task_name)
            os.makedirs(pred_dir, exist_ok=True)
            pred_path = os.path.join(pred_dir, f"{subtask}.json")
            with open(pred_path, "w", encoding="utf-8") as f:
                json.dump(pred_list, f, ensure_ascii=False, indent=2)
            print(f"[biomni] wrote {pred_path}", flush=True)

    print("All results under:", bench_run_dir, flush=True)
    print("RESULTS_DIR=" + os.path.abspath(bench_run_dir), flush=True)


if __name__ == "__main__":
    main()
