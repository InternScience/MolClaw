# Bench data loading and prediction entry building: load samples, get_query returns query as-is, parse extracts from <answer> and writes to pred.
from __future__ import annotations

import os
import re
import json
import csv
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

CHEMCOT_MOL_OPT_PHYSCHEM_SUBTASKS = ["logp", "qed", "solubility"]
CHEMCOT_MOL_OPT_TARGET_SUBTASKS = ["drd", "gsk", "jnk"]


def extract_answer_from_text(text: str) -> str:
    """Extract raw content of <answer>...</answer> from text (may be JSON or plain SMILES)."""
    if not text or not isinstance(text, str):
        return ""
    m = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    return (m.group(1) or "").strip()


def _answer_content_to_smiles(content: str, key: str) -> str:
    """Parse <answer> content to SMILES for evaluation. Supports JSON when bench requires it (mol_edit: output, mol_opt: Final Target Molecule), else plain SMILES."""
    if not content:
        return ""
    raw = content.strip()
    # Try JSON parse per bench (mol_edit: "output", mol_opt: "Final Target Molecule")
    try:
        # Allow wrapping in ```json etc.
        s = raw
        for prefix in ("```json\n", "```json", "```\n"):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
        d = json.loads(s)
        if isinstance(d, dict) and key in d:
            return (d[key] or "").strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return raw


def collect_result_text(result: Dict[str, Any]) -> str:
    """Collect readable text from agent execution result (for saving as raw)."""
    if not result:
        return ""
    finish = None
    for act in result.get("action_history") or result.get("loop_results") or []:
        if isinstance(act, dict):
            finish = act.get("finish") or act.get("finish_text") or finish
    if finish:
        return finish if isinstance(finish, str) else str(finish)
    # When no explicit finish (e.g. max_iter forced end), use summary content to extract <answer>
    for act in result.get("action_history") or result.get("loop_results") or []:
        if isinstance(act, dict) and act.get("type") == "summary" and act.get("content"):
            return str(act["content"])
    ctx = result.get("context") or {}
    for k, v in ctx.items():
        if isinstance(v, dict) and v.get("content"):
            return str(v["content"])[:2000]
    return json.dumps(result, ensure_ascii=False, indent=2)[:2000]


def _extract_mol_edit_input_molecule(query: str) -> str:
    """Extract Input Molecule SMILES from mol_edit query."""
    m = re.search(r"Input Molecule:\s*([^\n,]+)", query, re.IGNORECASE)
    return (m.group(1).strip() if m else "").strip()


def _extract_mol_opt_src_molecule(query: str) -> str:
    """Extract Source Molecule SMILES from mol_opt query."""
    m = re.search(r"Source Molecule:\s*([^\n.]+)", query, re.IGNORECASE)
    return (m.group(1).strip() if m else "").strip()


def _extract_mol_und_input_molecule(query: str) -> str:
    """Extract Input Molecule SMILES from mol_und query (ring_count, fg_count, ring_system_scaffold, Murcko_scaffold)."""
    m = re.search(r"Input Molecule:\s*([^\n,]+)", query, re.IGNORECASE)
    return (m.group(1).strip() if m else "").strip()


def _extract_mol_und_molecule_a(query: str) -> str:
    """Extract Molecule A SMILES from equivalence query."""
    m = re.search(r"Molecule A:\s*([^,]+),", query, re.IGNORECASE)
    return (m.group(1).strip() if m else "").strip()


def _load_chemcotbench_json(
    data_path: str,
    dir_candidates: List[str],
    subtask: str,
    max_samples: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Load a ChemCoTBench JSON file, preferring regrouped dirs and falling back to legacy layout."""
    candidate_paths: List[str] = []
    for task_dir in dir_candidates:
        candidate_paths.append(os.path.join(data_path, "chemcotbench", task_dir, f"{subtask}.json"))
        candidate_paths.append(os.path.join(data_path, task_dir, f"{subtask}.json"))
    path = next((p for p in candidate_paths if os.path.isfile(p)), "")
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if max_samples is not None and max_samples > 0:
        data = data[:max_samples]
    return data


def _answer_content_to_value(content: str, key: str) -> Optional[Any]:
    """Parse <answer> content: extract key from JSON (string or number), else return raw stripped string."""
    if not content:
        return None
    raw = content.strip()
    try:
        s = raw
        for prefix in ("```json\n", "```json", "```\n"):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
        d = json.loads(s)
        if isinstance(d, dict) and key in d:
            v = d[key]
            if v is None:
                return None
            if isinstance(v, (int, float)):
                return v
            return (v if isinstance(v, str) else str(v)).strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return raw.strip() if raw else None


# ---------- Base Loader ----------


class BaseBenchLoader(ABC):
    @abstractmethod
    def get_subtasks(self) -> List[str]:
        pass

    @abstractmethod
    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        pass

    def get_query(self, sample: Dict[str, Any], subtask: str) -> str:
        """Return bench raw query as-is to agent, no truncation or denoising."""
        return (sample.get("query") or "").strip()

    def get_extra_answer_hint(self, sample: Dict[str, Any], subtask: str) -> Optional[str]:
        """Optional task-specific hint for <answer> format (e.g. one SMILES per line). Default None."""
        return None

    @abstractmethod
    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        """Return data to write to .smi (current variable/file content) for agent use."""
        pass

    @abstractmethod
    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        """Parse structured fields needed for evaluation from agent result (e.g. output / Final Target Molecule)."""
        pass

    @abstractmethod
    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        pass


# ---------- ChemCoTBench mol_edit ----------


class ChemCoTBenchMolEditLoader(BaseBenchLoader):
    SUBTASKS = ["add", "delete", "sub"]

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        return _load_chemcotbench_json(data_path, ["molbench-mo-edit", "mol_edit"], subtask, max_samples)

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        raw = sample.get("query") or ""
        smi = _extract_mol_edit_input_molecule(raw)
        return smi if smi else ""

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        """Extract evaluation answer from <answer>; supports bench JSON {\"output\": \"SMILES\"} or plain SMILES."""
        out: Dict[str, Any] = {}
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        if ans:
            out["output"] = _answer_content_to_smiles(ans, "output")
        return out

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        raw_query = sample.get("query") or ""
        molecule = _extract_mol_edit_input_molecule(raw_query)
        meta = sample.get("meta") or "{}"
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        added_group = meta.get("added_group") or ""
        removed_group = meta.get("removed_group") or ""
        entry: Dict[str, Any] = {
            "molecule": molecule,
            "added_group": added_group,
            "removed_group": removed_group,
            "json_results": parsed,
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


# ---------- ChemCoTBench mol_opt ----------


class _ChemCoTBenchMolOptLoaderBase(BaseBenchLoader):
    SUBTASKS: List[str] = []
    DIR_CANDIDATES: List[str] = []

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        return _load_chemcotbench_json(data_path, self.DIR_CANDIDATES, subtask, max_samples)

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        raw_query = sample.get("query") or ""
        src_smiles = _extract_mol_opt_src_molecule(raw_query)
        return src_smiles if src_smiles else ""

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        """Extract per official: JSON key \"Final Target Molecule\" or \"Final_Target_Molecule\" (eval_molopt.py)."""
        out: Dict[str, Any] = {}
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        if not ans:
            return out
        smi = _answer_content_to_smiles(ans, "Final Target Molecule") or _answer_content_to_smiles(ans, "Final_Target_Molecule")
        if smi:
            out["Final Target Molecule"] = smi
        return out

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        raw_query = sample.get("query") or ""
        src_smiles = _extract_mol_opt_src_molecule(raw_query)
        entry: Dict[str, Any] = {
            "src_smiles": src_smiles,
            "prop": subtask,
            "json_results": parsed,
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


class ChemCoTBenchMolOptPhyschemLoader(_ChemCoTBenchMolOptLoaderBase):
    SUBTASKS = list(CHEMCOT_MOL_OPT_PHYSCHEM_SUBTASKS)
    DIR_CANDIDATES = ["molbench-mo-opt", "mol_opt_physchem", "mol_opt"]


class ChemCoTBenchMolOptTargetLoader(_ChemCoTBenchMolOptLoaderBase):
    SUBTASKS = list(CHEMCOT_MOL_OPT_TARGET_SUBTASKS)
    DIR_CANDIDATES = ["mol_opt_target", "mol_opt"]


class ChemCoTBenchMolOptLoader(_ChemCoTBenchMolOptLoaderBase):
    SUBTASKS = list(CHEMCOT_MOL_OPT_PHYSCHEM_SUBTASKS + CHEMCOT_MOL_OPT_TARGET_SUBTASKS)
    DIR_CANDIDATES = ["mol_opt"]


# ---------- ChemCoTBench mol_und ----------


class ChemCoTBenchMolUndLoader(BaseBenchLoader):
    SUBTASKS = ["equivalence", "fg_count", "Murcko_scaffold", "ring_count", "ring_system_scaffold"]

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        path = os.path.join(data_path, "chemcotbench", "mol_und", f"{subtask}.json")
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if max_samples is not None and max_samples > 0:
            data = data[:max_samples]
        return data

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        raw = sample.get("query") or ""
        if subtask == "equivalence":
            smi = _extract_mol_und_molecule_a(raw)
        else:
            smi = _extract_mol_und_input_molecule(raw)
        return smi if smi else ""

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        """Extract answer from <answer>; keys: output (Yes/No), count (int), Output Scaffold (SMILES)."""
        out: Dict[str, Any] = {}
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        if not ans:
            return out
        if subtask in ("equivalence", "ring_system_scaffold"):
            v = _answer_content_to_value(ans, "output")
            if v is not None:
                out["output"] = v
        elif subtask in ("ring_count", "fg_count"):
            v = _answer_content_to_value(ans, "count")
            if v is not None:
                try:
                    out["count"] = int(v) if isinstance(v, str) else v
                except (ValueError, TypeError):
                    out["count"] = v
        elif subtask == "Murcko_scaffold":
            v = _answer_content_to_value(ans, "Output Scaffold")
            if v is not None:
                out["Output Scaffold"] = (v if isinstance(v, str) else str(v)).strip()
        return out

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "gt": sample.get("gt"),
            "json_results": parsed,
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


# ---------- ChemCoTBench reaction ----------


class ChemCoTBenchReactionLoader(BaseBenchLoader):
    SUBTASKS = ["fs", "mechsel", "nepp", "rcr", "retro"]

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        path = os.path.join(data_path, "chemcotbench", "reaction", f"{subtask}.json")
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if max_samples is not None and max_samples > 0:
            data = data[:max_samples]
        return data

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        """Reaction tasks use query text only; no single .smi input."""
        return ""

    # Official ChemCoTBench answer keys per subtask (from bench query/gt format)
    REACTION_ANSWER_KEYS = {
        "fs": ("Major Product", "Byproduct(s)"),   # JSON: Major Product, optional Byproduct(s)
        "retro": ("Reactants",),                    # JSON: Reactants
        "rcr": ("SMILES",),                         # JSON: SMILES
        "nepp": ("pred_smi",),                      # JSON: pred_smi
        "mechsel": ("choice",),                     # JSON: choice (letter A-J)
    }

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        """Extract from <answer> using official bench keys per subtask. No fallback to other keys."""
        out: Dict[str, Any] = {}
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        if not ans:
            return out
        raw = ans.strip()
        try:
            s = raw
            for prefix in ("```json\n", "```json", "```\n"):
                if s.startswith(prefix):
                    s = s[len(prefix) :].strip()
            if s.endswith("```"):
                s = s[:-3].strip()
            d = json.loads(s)
            if not isinstance(d, dict):
                return out
            keys = self.REACTION_ANSWER_KEYS.get(subtask, ())
            if subtask == "fs":
                # Official eval uses Major Product only (rxn_eval_demo evaluate_fs)
                if "Major Product" in d and d["Major Product"] is not None:
                    out["SMILES"] = str(d["Major Product"]).strip()
            elif subtask == "mechsel":
                v = d.get("choice")
                if v is not None:
                    out["choice"] = str(v).strip().upper()[:1]
            else:
                # retro: Reactants; rcr: SMILES; nepp: pred_smi
                key = keys[0] if keys else None
                if key and key in d and d[key] is not None:
                    out["SMILES"] = str(d[key]).strip()
        except (json.JSONDecodeError, TypeError):
            pass
        return out

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "gt": sample.get("gt"),
            "json_results": parsed,
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


# ---------- ACNet_curated QA (pairwise Ki comparison) ----------


class ACNetCuratedLoader(BaseBenchLoader):
    """ACNet_curated QA bench loader.

    Contract:
    - data_path must point to a CSV file with header:
    question,answer,target
    (legacy optional columns: s1,k1,s2,k2)
    - subtask is fixed to "qa"
    - evaluation is exact string match between <answer>...</answer> content and ground-truth answer.
    """

    SUBTASKS = ["qa"]
    REQUIRED_COLUMNS = ["question", "answer", "target"]
    OPTIONAL_COLUMNS = ["s1", "k1", "s2", "k2"]

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        if subtask != "qa":
            raise ValueError(f"ACNet_curated only supports subtask 'qa', got: {subtask}")
        if not os.path.isfile(data_path):
            raise FileNotFoundError(f"ACNet_curated CSV not found: {data_path}")
        # Use utf-8-sig to handle an optional UTF-8 BOM deterministically.
        with open(data_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            missing = [c for c in self.REQUIRED_COLUMNS if c not in header]
            if missing:
                raise ValueError(f"ACNet_curated CSV missing required columns: {missing}")
            optional_columns = [c for c in self.OPTIONAL_COLUMNS if c in header]
            data: List[Dict[str, Any]] = []
            for row in reader:
                q = (row.get("question") or "").strip()
                a = (row.get("answer") or "").strip()
                if not q or not a:
                    raise ValueError("ACNet_curated CSV contains empty question or answer")
                sample: Dict[str, Any] = {
                    "query": q,
                    "gt": a,
                    "target": (row.get("target") or "").strip(),
                }
                for col in optional_columns:
                    sample[col] = (row.get(col) or "").strip()
                data.append(sample)
        if max_samples is not None and max_samples > 0:
            data = data[:max_samples]
        return data

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        # This QA bench uses question text only; no external .smi input is required.
        return ""

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        return {"output": ans}

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "gt": sample.get("gt") or "",
            "json_results": parsed,
            "user_query": sample.get("query") or "",
            "target": sample.get("target") or "",
            "s1": sample.get("s1") or "",
            "k1": sample.get("k1") or "",
            "s2": sample.get("s2") or "",
            "k2": sample.get("k2") or "",
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


# ---------- Virtual_Screening_curated (Top-3 virtual screening) ----------


class VirtualScreeningCuratedLoader(BaseBenchLoader):
    """Virtual_Screening_curated bench loader.

    Contract:
    - data_path must point to a CSV file with header:
      prompt,task_type,answer
    - Each row is one test sample:
      * prompt: JSON string (English) describing target, assay endpoint and 60 candidate SMILES
      * task_type: "zero-shot" or "few-shot"
      * answer: JSON array of SMILES (subset of candidates) that meet the activity threshold
    - subtask is fixed to "virtual_screening_curated"
    """

    SUBTASKS = ["virtual_screening_curated"]
    REQUIRED_COLUMNS = ["task_type", "answer"]

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        if subtask != "virtual_screening_curated":
            raise ValueError(f"Virtual_Screening_curated only supports subtask 'virtual_screening_curated', got: {subtask}")
        if not os.path.isfile(data_path):
            raise FileNotFoundError(f"Virtual_Screening_curated CSV not found: {data_path}")
        # Use utf-8-sig to handle an optional UTF-8 BOM deterministically.
        with open(data_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            missing = [c for c in self.REQUIRED_COLUMNS if c not in header]
            if missing:
                raise ValueError(f"Virtual_Screening_curated CSV missing required columns: {missing}")
            if "prompt" not in header and "questions" not in header:
                raise ValueError("Virtual_Screening_curated CSV must have either 'prompt' or 'questions' column")
            data: List[Dict[str, Any]] = []
            for row in reader:
                prompt = (row.get("prompt") or row.get("questions") or "").strip()
                task_type = (row.get("task_type") or "").strip()
                answer_raw = (row.get("answer") or "").strip()
                if not prompt or not answer_raw:
                    raise ValueError("Virtual_Screening_curated CSV contains empty prompt or answer")
                try:
                    answer_list = json.loads(answer_raw)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Virtual_Screening_curated CSV has invalid JSON in answer column: {e}") from e
                if not isinstance(answer_list, list):
                    raise ValueError("Virtual_Screening_curated CSV answer must be a JSON array")
                # Parse prompt JSON: extract candidates for .smi file; build short query with #candidates.smi.
                try:
                    prompt_obj = json.loads(prompt) if isinstance(prompt, str) and prompt.strip().startswith("{") else {}
                except json.JSONDecodeError:
                    prompt_obj = {}
                candidates = list(prompt_obj.get("candidates") or []) if isinstance(prompt_obj.get("candidates"), list) else []
                data.append(
                    {
                        "query": prompt,
                        "query_meta": prompt_obj,
                        "candidates": candidates,
                        "task_type": task_type,
                        "answer": answer_list,
                    }
                )
        if max_samples is not None and max_samples > 0:
            data = data[:max_samples]
        return data

    def get_query(self, sample: Dict[str, Any], subtask: str) -> str:
        """Short query with task meta; candidates are in #candidates.smi (injected via get_dataset_content)."""
        meta = sample.get("query_meta") or {}
        if not meta and sample.get("query"):
            try:
                meta = json.loads(sample["query"]) if isinstance(sample["query"], str) and (sample["query"] or "").strip().startswith("{") else {}
            except json.JSONDecodeError:
                meta = {}
        task = meta.get("task") or "From the candidate molecules, identify the 3 most potent compounds."
        output_format = meta.get("output_format") or "Return a JSON array of exactly 3 SMILES strings, ranked from most to least potent."
        target = meta.get("target_chembl_id") or meta.get("target") or ""
        assay = meta.get("assay_endpoint") or ""
        note = meta.get("note") or ""
        parts = [f"Task: {task}", f"Output format: {output_format}"]
        if target:
            parts.append(f"Target: {target}")
        if assay:
            parts.append(f"Assay endpoint: {assay}")
        if note:
            parts.append(f"Note: {note}")
        if sample.get("candidates"):
            parts.append("Candidate molecules (one SMILES per line): #candidates.smi")
        return "\n".join(parts)

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        """One SMILES per line for .smi file; written as candidates.smi so query can use #candidates.smi."""
        candidates = sample.get("candidates") or []
        return "\n".join(str(s).strip() for s in candidates if s is not None)

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        """Extract model Top-3 predictions from <answer> JSON array."""
        out: Dict[str, Any] = {}
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        if not ans:
            return out
        raw = ans.strip()
        try:
            s = raw
            for prefix in ("```json\n", "```json", "```\n"):
                if s.startswith(prefix):
                    s = s[len(prefix):].strip()
            if s.endswith("```"):
                s = s[:-3].strip()
            parsed = json.loads(s)
            if isinstance(parsed, list):
                # Enforce list-of-strings contract; non-string entries are stringified.
                top3: List[str] = []
                for v in parsed:
                    if v is None:
                        continue
                    top3.append(v if isinstance(v, str) else str(v))
                out["top3"] = top3
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, leave out["top3"] unset; eval will treat as empty prediction.
            pass
        return out

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "user_query": sample.get("query") or "",
            "task_type": sample.get("task_type") or "",
            # Ground-truth SMILES list for evaluation.
            "answer": list(sample.get("answer") or []),
            "json_results": parsed,
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


class MolbenchVsLoader(BaseBenchLoader):
    """Loader for Molbench-vs docking ranking benchmark."""

    SUBTASKS = ["molbench_vs"]
    REQUIRED_COLUMNS = ["index", "questions", "answer"]

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        if subtask != "molbench_vs":
            raise ValueError(f"Molbench_vs only supports subtask 'molbench_vs', got: {subtask}")
        if not os.path.isfile(data_path):
            raise FileNotFoundError(f"Molbench_vs CSV not found: {data_path}")
        with open(data_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            missing = [c for c in self.REQUIRED_COLUMNS if c not in header]
            if missing:
                raise ValueError(f"Molbench_vs CSV missing required columns: {missing}")
            data: List[Dict[str, Any]] = []
            for row in reader:
                idx = (row.get("index") or "").strip()
                questions = (row.get("questions") or "").strip()
                answer_raw = (row.get("answer") or "").strip()
                try:
                    meta = json.loads(questions) if questions else {}
                except Exception:
                    meta = {}
                if not isinstance(meta, dict):
                    meta = {}
                candidates = [str(s).strip() for s in (meta.get("candidates") or []) if s]
                answer_list: List[str] = []
                if answer_raw:
                    try:
                        parsed_answer = json.loads(answer_raw)
                        if isinstance(parsed_answer, list):
                            answer_list = [str(s).strip() for s in parsed_answer if s]
                    except Exception:
                        answer_list = []
                data.append(
                    {
                        "index": idx,
                        "query_meta": meta,
                        "raw_query": questions,
                        "candidates": candidates,
                        "answer": answer_list,
                    }
                )
        if max_samples is not None and max_samples > 0:
            data = data[:max_samples]
        return data

    def get_query(self, sample: Dict[str, Any], subtask: str) -> str:
        meta = sample.get("query_meta") or {}
        if not meta and sample.get("raw_query"):
            return sample.get("raw_query", "")
        parts: List[str] = []
        task = meta.get("task") or "Rank the candidate molecules by docking score."
        objective = meta.get("objective")
        output_format = meta.get("output_format")
        target = meta.get("target_name") or meta.get("target_chembl_id") or meta.get("target")
        note = meta.get("note")
        parts.append(f"Task: {task}")
        if objective:
            parts.append(f"Objective: {objective}")
        if output_format:
            parts.append(f"Output format: {output_format}")
        if target:
            parts.append(f"Target: {target}")
        if meta.get("assay_endpoint"):
            parts.append(f"Assay endpoint: {meta.get('assay_endpoint')}")
        if note:
            parts.append(f"Note: {note}")
        if sample.get("candidates"):
            parts.append("Candidate molecules: #candidates.smi (one SMILES per line)")
        return "\n".join(parts)

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        candidates = sample.get("candidates") or []
        return "\n".join(str(s).strip() for s in candidates if s)

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        if not ans:
            return out
        raw = ans.strip()
        for prefix in ("```json\n", "```json", "```\n"):
            if raw.startswith(prefix):
                raw = raw[len(prefix) :].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                top3: List[str] = []
                for v in parsed:
                    if v is None:
                        continue
                    v_str = str(v).strip()
                    if v_str:
                        top3.append(v_str)
                if top3:
                    out["top3"] = top3[:3]
        except Exception:
            return out
        return out

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "index": sample.get("index") or "",
            "user_query": sample.get("raw_query") or "",
            "answer": list(sample.get("answer") or []),
            "candidates": [str(s).strip() for s in sample.get("candidates") or [] if s],
            "json_results": parsed,
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


# ---------- RDKit_bench (constraint filtering: prompt + answer) ----------


class RdkitBenchLoader(BaseBenchLoader):
    """RDKit benchmark: CSV with prompt, answer, meta. One subtask; metric acc (exact set-of-lines match)."""

    SUBTASKS = ["rdkit_bench"]
    REQUIRED_COLUMNS = ["answer"]
    PROMPT_COLUMNS = ("prompt", "question")

    def get_subtasks(self) -> List[str]:
        return list(self.SUBTASKS)

    def load_data(self, data_path: str, subtask: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        if subtask != "rdkit_bench":
            raise ValueError(f"RdkitBench only supports subtask 'rdkit_bench', got: {subtask}")
        if not os.path.isfile(data_path):
            raise FileNotFoundError(f"RdkitBench CSV not found: {data_path}")
        data: List[Dict[str, Any]] = []
        with open(data_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            missing = [c for c in self.REQUIRED_COLUMNS if c not in header]
            if missing:
                raise ValueError(f"RdkitBench CSV missing columns: {missing}")
            prompt_col = next((c for c in self.PROMPT_COLUMNS if c in header), None)
            if prompt_col is None:
                raise ValueError(f"RdkitBench CSV missing prompt column; expected one of {list(self.PROMPT_COLUMNS)}")
            for row in reader:
                prompt = (row.get(prompt_col) or "").strip()
                answer = (row.get("answer") or "").strip()
                if not prompt:
                    continue
                data.append({"query": prompt, "gt": answer, "meta": row.get("meta") or ""})
        if max_samples is not None and max_samples > 0:
            data = data[:max_samples]
        return data

    def get_query(self, sample: Dict[str, Any], subtask: str) -> str:
        return (sample.get("query") or "").strip()

    def get_extra_answer_hint(self, sample: Dict[str, Any], subtask: str) -> Optional[str]:
        from MolClaw.molclaw_run.templates.template import RDKIT_ANSWER_HINT
        return RDKIT_ANSWER_HINT

    def get_dataset_content(self, sample: Dict[str, Any], subtask: str) -> str:
        return ""

    def parse_agent_result(self, result: Dict[str, Any], subtask: str) -> Dict[str, Any]:
        text = collect_result_text(result)
        ans = extract_answer_from_text(text)
        return {"output": ans}

    def build_pred_entry(self, sample: Dict[str, Any], parsed: Dict[str, Any], raw_text: str, subtask: str) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "query": sample.get("query") or "",
            "gt": sample.get("gt") or "",
            "json_results": parsed,
        }
        if raw_text:
            entry["raw_text"] = raw_text[:2000]
        return entry


# ---------- Loader registry ----------


LOADERS: Dict[str, BaseBenchLoader] = {
    "mol_edit": ChemCoTBenchMolEditLoader(),
    "molbench-mo-edit": ChemCoTBenchMolEditLoader(),
    "mol_opt_physchem": ChemCoTBenchMolOptPhyschemLoader(),
    "molbench-mo-opt": ChemCoTBenchMolOptPhyschemLoader(),
    "mol_opt_target": ChemCoTBenchMolOptTargetLoader(),
    "mol_opt": ChemCoTBenchMolOptLoader(),
    "mol_und": ChemCoTBenchMolUndLoader(),
    "reaction": ChemCoTBenchReactionLoader(),
    "acnet_curated": ACNetCuratedLoader(),
    "virtual_screening_curated": VirtualScreeningCuratedLoader(),
    "rdkit_bench": RdkitBenchLoader(),
    "molbench_vs": MolbenchVsLoader(),
}


def get_loader(task_name: str) -> Optional[BaseBenchLoader]:
    return LOADERS.get(task_name)
