from __future__ import annotations

import time
from typing import Dict, List, Optional, Any

import requests
from fastapi import APIRouter, HTTPException, Query

from backend.config import logger
from backend.core.config import settings

try:
    import google.generativeai as genai
except Exception:
    genai = None

router = APIRouter()


class _TTLCache:
    def __init__(self, ttl_seconds: int = 180) -> None:
        self.ttl = ttl_seconds
        self._data: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        hit = self._data.get(key)
        if not hit:
            return None
        ts, val = hit
        if time.time() - ts > self.ttl:
            self._data.pop(key, None)
            return None
        return val

    def set(self, key: str, val: Any) -> None:
        self._data[key] = (time.time(), val)


_cache = _TTLCache(ttl_seconds=180)


# ---- provider-specific resolvers ----
def _models_gemini_fixed() -> List[str]:
    # Static Gemini server-side OCR-friendly models (per your spec)
    return [
        "gemini-2.5-flash-image-preview",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite-001",
        "gemini-1.5-pro",
        "gemini-pro-vision",
        "gemini-1.5-flash"
    ]


def _models_mistral_ocr() -> List[str]:
    return ["mistral-ocr-latest", "mistral-ocr-2503", "mistral-ocr-2505"]


def _models_vllm() -> List[str]:
    if settings.VLLM_MODELS:
        return list(settings.VLLM_MODELS)
    return [
        "google/gemma-3-4b-it",
        "google/gemma-3-8b-it",
        "google/gemma-3-12b-it",
        "google/gemma-3-27b-it",
    ]


def _models_gemini_open_source() -> List[str]:
    cache_key = "gemini_open_source"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    fallback = ["models/gemma-3-4b-it", "models/gemma-3-12b-it"]
    if not genai or not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_OPENSOURCE listing unavailable, returning fallback.")
        _cache.set(cache_key, fallback)
        return fallback

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        models = genai.list_models()
        names = [
            m.name for m in models
            if hasattr(m, "supported_generation_methods")
               and "generateContent" in (m.supported_generation_methods or [])
        ]
        if not names:
            names = fallback
        _cache.set(cache_key, names)
        return names
    except Exception as e:  # pragma: no cover
        logger.error("Failed to list Gemini models, using fallback: %s", e)
        _cache.set(cache_key, fallback)
        return fallback


def _models_ollama() -> List[str]:
    cache_key = "ollama"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    endpoint = (settings.OLLAMA_ENDPOINT or "http://localhost:11434").rstrip("/")
    try:
        r = requests.get(f"{endpoint}/api/tags", timeout=10)
        if r.status_code == 200:
            data = r.json() or {}
            names = [m.get("name") for m in data.get("models", []) if m.get("name")]
            if names:
                _cache.set(cache_key, names)
                return names
        logger.warning("OLLAMA /api/tags returned %s; using fallback.", r.status_code)
    except Exception as e:  # pragma: no cover
        logger.warning("OLLAMA listing failed (%s); using fallback.", e)

    fallback = ["gemma2:4b", "llava:7b", "gemma2:8b"]
    _cache.set(cache_key, fallback)
    return fallback


def get_ocr_models_for(provider: str) -> List[str]:
    p = (provider or "").upper().strip()
    if p == "GEMINI":
        return _models_gemini_fixed()
    if p == "MISTRAL":
        return _models_mistral_ocr()
    if p == "GEMINI_OPENSOURCE":
        return _models_gemini_open_source()
    if p == "OLLAMA":
        return _models_ollama()
    if p == "VLLM":
        return _models_vllm()
    if p == "NONE":
        return []
    raise HTTPException(status_code=400, detail=f"Unknown OCR provider: {provider}")


def get_correction_models_for(provider: str) -> List[str]:
    """
    Simple approach: reuse the same discovery per provider for correction.
    Adjust here if your correction model sets differ from OCR.
    """
    return get_ocr_models_for(provider)


def all_ocr_models_by_provider() -> Dict[str, List[str]]:
    providers = ["GEMINI", "MISTRAL", "GEMINI_OPENSOURCE", "OLLAMA", "VLLM", "NONE"]
    return {p: get_ocr_models_for(p) for p in providers}


def all_correction_models_by_provider() -> Dict[str, List[str]]:
    providers = ["GEMINI", "MISTRAL", "GEMINI_OPENSOURCE", "OLLAMA", "VLLM", "NONE"]
    return {p: get_correction_models_for(p) for p in providers}


@router.get("", summary="List models by provider")
def list_models(
        ocr_provider: Optional[str] = Query(
            None,
            description="e.g., GEMINI | MISTRAL | GEMINI_OPENSOURCE | OLLAMA | VLLM | NONE"
        ),
        correction_provider: Optional[str] = Query(
            None,
            description="same provider set, but for correction"
        ),
):
    """
    - If query params provided, return just those lists.
    - If none provided, default to MISTRAL for both OCR & correction.
    - Entire response is cached per (ocr_provider, correction_provider) for TTL seconds.
    """
    # normalize & apply defaults (kept behavior)
    norm_ocr = (ocr_provider or "MISTRAL").upper().strip()
    norm_corr = (correction_provider or "MISTRAL").upper().strip()

    cache_key = f"list_models:{norm_ocr}:{norm_corr}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # compute on miss
    resp: Dict[str, object] = {
        "ocr": get_ocr_models_for(norm_ocr),
        "correction": get_correction_models_for(norm_corr),
    }

    _cache.set(cache_key, resp)
    return resp
