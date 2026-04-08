# Config Examples (Minimal Open-Source)

This directory keeps only minimal runnable examples.

## Organization

- baseline_molbench-ms-1.yaml: pure LLM on molbench-ms-1
- baseline_molbench-ms-2.yaml: pure LLM on molbench-ms-2
- baseline_molbench-ms-3.yaml: pure LLM on molbench-ms-3
- chemcot_mo_edit.yaml: pure LLM on molbench-mo-edit
- chemcot_mo_opt.yaml: pure LLM on molbench-mo-opt
- claude_template.yaml: Claude Code runner template

## Credential Policy

Do not put base_url/api_key in YAML examples.

Use environment variables:
- OPENAI_API_KEY
- OPENAI_BASE_URL

## Why this layout

- One config per benchmark for direct reproducibility.
- One template for Claude Code for quick adaptation.
- No internal endpoints or secret-bearing fields.
