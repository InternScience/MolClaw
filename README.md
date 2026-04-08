# MolClaw

MolClaw 是一个面向分子任务的基准评测与技能驱动执行框架，旨在统一地测试不同模型在分子编辑、性质优化与虚拟筛选等任务上的表现。

- 论文（bioRxiv）：https://www.biorxiv.org/content/10.64898/2026.04.03.716272v1

## 项目结构

- `molbench/`: 基准评测数据与官方评测代码
- `skills/`: 可复用的化学/分子相关技能（给 Claude Code 使用）
- `molclaw_run/`: 运行器与数据加载器（baseline + Claude Code）
- `config/`: 最小可运行配置模板
- `utils/`: 通用工具（例如 LLM 端点与随机种子）

### molbench

`molbench` 目录下分为 `data` 与 `eval` 两部分：

- `molbench/data/`：
  - `molbench-ms-1`：约束过滤任务（原 RDKit_bench）
  - `molbench-ms-2`：结合亲和力问答（原 ACNet_curated）
  - `molbench-ms-3`：虚拟筛选排序（原 MolBench-vs）
  - `molbench-mo`：ChemCoTBench 任务子集（molbench-mo-edit / molbench-mo-opt）

- `molbench/eval/`：
  - `ChemCoTBench/`：官方评测代码与依赖
  - `eval_runner.py` / `run_eval_bench.py`：本项目统一评测入口

### skills

`skills/` 提供给 Claude Code 的可调用技能。典型使用方式是将 `skills/` 中的技能复制到当前工作目录的 `./.claude/skills/` 下，让 Claude Code 在本地推理时调用。

### molclaw_run

`molclaw_run` 仅保留两类入口：

- `infer/baselines/`: 纯 LLM baseline 跑法
- `infer/claude_agent/`: Claude Code 跑法

数据加载与解析逻辑在 `molclaw_run/data_loader/` 中。

## 支持的基座模型（示例）

- GPT-4o
- GPT 5.2
- Gemini 3
- Claude Sonnet 4.6
- Deepseek V3.2
- GLM 5
- Minimax 2.5
- Kimi 2.5
- Intern-S1-Pro

> 具体模型名称由 `config/*.yaml` 的 `model.llm_model` 决定，并通过环境变量配置 API 端点与密钥。

## Quickstart

### 1) 单条问题（Claude Code）

1. 复制技能到工作目录：

```bash
mkdir -p ./.claude/skills
cp -R /Users/sunx/code_proj/MolClaw/skills/* ./.claude/skills/
```

2. 在终端启动 Claude Code：

```bash
claude
```

3. 在 Claude Code 中执行初始化：

```
/init
```

4. 这会生成 `CLAUDE.md`，随后即可直接提问。

### 2) molbench 测试（baseline）

以 `molbench-ms-1` 为例：

```bash
export OPENAI_API_KEY=YOUR_KEY
export OPENAI_BASE_URL=YOUR_BASE_URL

python molclaw_run/infer/baselines/run_baseline.py --cfg config/baseline_molbench-ms-1.yaml
# 输出会包含 RESULTS_DIR=... 

python molbench/eval/run_eval_bench.py <RESULTS_DIR> --cfg config/baseline_molbench-ms-1.yaml
```

### 3) molbench 测试（Claude Code）

```bash
export OPENAI_API_KEY=YOUR_KEY
export OPENAI_BASE_URL=YOUR_BASE_URL

bash molclaw_run/infer/claude_agent/launch_claude.sh --cfg config/claude_template.yaml --claude-mode both
```

### 4) ChemCoTBench（molbench-mo）评测

```bash
python molbench/eval/run_eval_bench.py <RESULTS_DIR> --cfg config/chemcot_mo_edit.yaml
python molbench/eval/run_eval_bench.py <RESULTS_DIR> --cfg config/chemcot_mo_opt.yaml
```

## 环境变量

- `OPENAI_API_KEY`：模型服务密钥
- `OPENAI_BASE_URL`：模型服务端点

## License

尚未指定。如果需要开源许可证，请新增 `LICENSE` 文件。
