from pathlib import Path
from typing import List, Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory (parent of core/)
BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Pydantic Settings config
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    APP_NAME: str = "Visionary OCR API"
    API_V1_PREFIX: str = "/v1"
    ENV: Literal["development", "staging", "production"] = "production"

    # CORS (set explicit origins in prod)
    CORS_ORIGINS: List[str] = ["*"]

    # Optional simple API key auth (leave empty to disable)
    API_KEY: Optional[str] = None
    API_KEY_HEADER: str = "x-api-key"

    # Provider defaults (front-end may pass "PROVIDER:MODEL")
    DEFAULT_OCR_PROVIDER: Literal["GEMINI", "MISTRAL", "OLLAMA", "VLLM", "GEMINI_OPENSOURCE", "NONE"] = "MISTRAL"
    DEFAULT_CORRECTION_PROVIDER: Literal[
        "GEMINI", "MISTRAL", "OLLAMA", "VLLM", "GEMINI_OPENSOURCE", "NONE"] = "GEMINI_OPENSOURCE"

    # (Optional) legacy dropdown seeds — safe to keep for UI
    OCR_MODELS: List[str] = ["ocr-latest", "gemini-gemma-3-4b-it", "mistral-small"]
    CORRECTION_MODELS: List[str] = ["gemini-1.5-pro", "mistral-small-latest"]

    MISTRAL_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_ENDPOINT: str = "http://localhost:11434"  # prefer this name
    VLLM_SERVER_URL: Optional[str] = None
    VLLM_MODELS: List[str] = []  # optional static list for VLLM

    # --- Back-compat alias (if you had OLLAMA_API in old code) ---
    # Define but don't use elsewhere; set OLLAMA_ENDPOINT in .env instead.
    OLLAMA_API: Optional[str] = None


settings = Settings()
