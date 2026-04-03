# Open Source Minimal Test Edition

This folder is the minimal open-source test package for MolBench-MS, MolBench-MO style benchmark runs.

## Supported test dimensions

### Agent types
- pure-llm
- biomni
- claude-code
- openclaw
- nanobot

### Datasets
- molbench-ms-1 (renamed from RDKit)
- molbench-ms-2 (renamed from ACNet)
- molbench-ms-3 (renamed from MolBench-vs)
- ChemCoTBench curated tasks
  - molbench-mo-edit
  - molbench-mo-opt

### Base models
- GPT-4o
- GPT 5.2
- Gemini 3
- Claude Sonnet 4.6
- Deepseek V3.2
- GLM 5
- Minimax 2.5
- Kimi 2.5
- Intern-S1-Pro

## Minimal directory layout

- bench/
  - molbench-ms-1/molbench-ms-1.csv
  - molbench-ms-2/molbench-ms-2.csv
  - molbench-ms-3/molbench-ms-3.csv
  - molbench-mo/molbench-mo-edit/
  - molbench-mo/molbench-mo-opt/
  - ChemCoTBench/baseline_and_eval/
- config/
  - baseline_molbench-ms-1.yaml
  - baseline_molbench-ms-2.yaml
  - baseline_molbench-ms-3.yaml
  - chemcot_mo_edit.yaml
  - chemcot_mo_opt.yaml
  - biomni_template.yaml
  - claude_template.yaml
  - openclaw_template.yaml
  - nanobot_template.yaml
- molclaw_run/
  - infer/baselines/run_baseline.py
  - infer/biomni/run_biomni.py
  - infer/claude_agent/run_claude.py
  - infer/openclaw_agent/run_openclaw.py
  - infer/nanobot_agent/run_nanobot.py
  - evaluate/run_eval_bench.py

## Credentials and endpoint policy

Hardcoded keys and private endpoints were removed.

Use environment variables defined via .env.template:
- OPENAI_API_KEY
- OPENAI_BASE_URL (optional)
- NANOBOT_MCP_URL (optional)
- NANOBOT_MCP_API_KEY (optional)

Load env before running scripts:

```bash
set -a
source .env
set +a
```

## ChemCoTBench note

`bench/ChemCoTBench/baseline_and_eval` is still required for official `molbench-mo-edit` and `molbench-mo-opt` evaluation. Do not delete it unless you also replace the official ChemCoT evaluation path in code.

## Quick start examples

Run pure LLM on molbench-ms-1:

```bash
python molclaw_run/infer/baselines/run_baseline.py --cfg config/baseline_molbench-ms-1.yaml
```

Run eval for a finished run directory:

```bash
python molclaw_run/evaluate/run_eval_bench.py <RESULTS_DIR> --cfg config/baseline_molbench-ms-1.yaml
```
