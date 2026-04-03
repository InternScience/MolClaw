from __future__ import annotations

import os
from typing import Any, Dict, Optional


def _get_required_env(name: str, default: str | None = None) -> str:
    value = (os.getenv(name) or "").strip()
    if value:
        return value
    if default is not None:
        return default
    return ""


DEFAULT_OPENAI_BASE_URL = ""

MODEL_ALIASES: Dict[str, str] = {
    "minimax": "minimax2.5",
    "minimax2.5": "minimax2.5",
    "glm": "glm-5",
    "glm5": "glm-5",
    "glm-5": "glm-5",
    "deepseek": "deepseek-v3.2",
    "deepseek-v3.2": "deepseek-v3.2",
    "kimi": "kimi-k2.5",
    "kimi-k2.5": "kimi-k2.5",
    "qwen3.5-397b": "qwen3.5-397b",
    "intern-s1": "intern-s1",
    "intern-s1-pro": "intern-s1-pro",
}


def canonical_model(model_name: Optional[str]) -> str:
    name = (model_name or "").strip()
    if not name:
        return ""
    return MODEL_ALIASES.get(name.lower(), name)


def resolve_openai_base_url(model_name: Optional[str] = None, cfg_base_url: Optional[str] = None) -> str:
    cfg_url = (cfg_base_url or "").strip()
    if cfg_url:
        return cfg_url
    env_url = (os.getenv("OPENAI_BASE_URL") or "").strip()
    if env_url:
        return env_url
    return DEFAULT_OPENAI_BASE_URL


def resolve_openai_api_key(cfg_model: Optional[Dict[str, Any]] = None) -> str:
    cfg_model = cfg_model or {}
    cfg_api_key = (cfg_model.get("api_key") or "").strip()
    cfg_api_key_env = (cfg_model.get("api_key_env") or "").strip()
    if cfg_api_key:
        return cfg_api_key
    if cfg_api_key_env:
        return (os.getenv(cfg_api_key_env) or "").strip()
    return (os.getenv("OPENAI_API_KEY") or "").strip()


OPENAI_BASE_URL = resolve_openai_base_url()
OPENAI_API_KEY = resolve_openai_api_key()
