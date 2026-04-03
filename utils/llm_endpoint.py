from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple


DEFAULT_OPENAI_BASE_URL = ""

MODEL_ALIASES: Dict[str, str] = {
    "minimax2.5": "minimax2.5",
    "minimax": "minimax2.5",
    "glm-5": "glm-5",
    "glm5": "glm-5",
    "glm": "glm-5",
    "deepseek": "deepseek-v3.2",
    "deepseek-v3.2": "deepseek-v3.2",
    "kimi-k2.5": "kimi-k2.5",
    "kimi": "kimi-k2.5",
    "qwen3.5-397b": "qwen3.5-397b",
    "intern-s1": "intern-s1",
    "intern-s1-pro": "intern-s1-pro",
}


def _canonical_model(model_name: Optional[str]) -> str:
    name = (model_name or "").strip()
    if not name:
        return ""
    return MODEL_ALIASES.get(name.lower(), name)


def resolve_openai_client_kwargs(
    llm_model: Optional[str],
    *,
    cfg_model: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, str], str]:
    """Resolve OpenAI client kwargs and canonical model name.

    Priority for base_url:
    1) cfg model.base_url
    2) OPENAI_BASE_URL env
    3) project default endpoint

    Priority for api_key:
    1) cfg model.api_key
    2) env var named by cfg model.api_key_env
    3) OPENAI_API_KEY env
    4) raise error (must be configured explicitly)
    """
    cfg_model = cfg_model or {}
    canonical_model = _canonical_model(llm_model)

    cfg_base_url = (cfg_model.get("base_url") or "").strip()
    cfg_api_key = (cfg_model.get("api_key") or "").strip()
    cfg_api_key_env = (cfg_model.get("api_key_env") or "").strip()

    base_url = (
        cfg_base_url
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or DEFAULT_OPENAI_BASE_URL
    )

    if cfg_api_key:
        api_key = cfg_api_key
    elif cfg_api_key_env:
        api_key = os.environ.get(cfg_api_key_env, "").strip()
    else:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("Missing OpenAI API key. Set model.api_key, model.api_key_env, or OPENAI_API_KEY.")

    return {"base_url": base_url, "api_key": api_key}, canonical_model


def apply_openai_env(
    llm_model: Optional[str],
    *,
    cfg_model: Optional[Dict[str, Any]] = None,
) -> str:
    """Apply resolved OpenAI env vars for child processes/scripts.

    Returns canonical model name to be used in requests.
    """
    kwargs, canonical_model = resolve_openai_client_kwargs(llm_model, cfg_model=cfg_model)
    os.environ["OPENAI_BASE_URL"] = kwargs["base_url"]
    os.environ["OPENAI_API_KEY"] = kwargs["api_key"]
    if canonical_model:
        os.environ["LLM_MODEL"] = canonical_model
    return canonical_model
