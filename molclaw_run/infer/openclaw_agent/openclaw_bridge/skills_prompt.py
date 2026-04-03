import os
from pathlib import Path


def _skills_roots() -> list[Path]:
    env_root = (os.getenv("DRUGAGENT_SKILLS_ROOT") or "").strip()
    if env_root:
        return [Path(p.strip()) for p in env_root.split(":") if p.strip()]
    return []


def _first_non_empty_line(text: str) -> str:
    for line in (text or "").splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def skills_catalog_text() -> str:
    roots = _skills_roots()
    if not roots:
        return ""
    lines = ["Available skills:"]
    for root in roots:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            skill_md = d / "SKILL.md"
            if not skill_md.is_file():
                continue
            try:
                desc = _first_non_empty_line(skill_md.read_text(encoding="utf-8"))
            except Exception:
                desc = ""
            label = d.name
            lines.append(f"- {label}: {desc}" if desc else f"- {label}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines).strip()


def choose_skill_prompt(user_task: str) -> str:
    catalog = skills_catalog_text()
    return (
        "Pick exactly ONE skill name from the list below. Reply with ONLY the skill name.\n\n"
        f"{catalog}\n\n"
        "Task:\n"
        f"{user_task}\n"
    ).strip()


def load_skill_text(skill_name: str) -> str:
    if not skill_name:
        return ""
    for root in _skills_roots():
        skill_md = root / skill_name / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            return skill_md.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def skill_env_root_hint() -> str:
    root = (os.getenv("DRUGAGENT_SKILLS_ROOT") or "").strip()
    mode = (os.getenv("DRUGAGENT_SKILLS_SOURCE_MODE") or "both").strip()
    parts = []
    if root:
        parts.append(f"DRUGAGENT_SKILLS_ROOT={root}")
    if mode:
        parts.append(f"DRUGAGENT_SKILLS_SOURCE_MODE={mode}")
    return " ".join(parts)


