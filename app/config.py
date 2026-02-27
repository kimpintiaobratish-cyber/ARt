from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "memory.db"


@dataclass
class AppConfig:
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = "http://localhost"
    openrouter_app_title: str = "Always-On Coding Tutor"
    whisper_model: str = "small"
    piper_binary: str = "piper"
    piper_model_path: str = ""
    save_screenshots: bool = False
    vision_mode: str = "AUTO"
    default_capture_mode: str = "active_window"


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    load_dotenv(BASE_DIR / ".env")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    cfg = AppConfig(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
        openrouter_http_referer=os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost").strip(),
        openrouter_app_title=os.getenv("OPENROUTER_APP_TITLE", "Always-On Coding Tutor").strip(),
        whisper_model=os.getenv("WHISPER_MODEL", "small").strip(),
        piper_binary=os.getenv("PIPER_BINARY", "piper").strip(),
        piper_model_path=os.getenv("PIPER_MODEL_PATH", "").strip(),
        save_screenshots=_as_bool(os.getenv("SAVE_SCREENSHOTS"), default=False),
        vision_mode=os.getenv("VISION_MODE", "AUTO").strip().upper(),
        default_capture_mode=os.getenv("DEFAULT_CAPTURE_MODE", "active_window").strip(),
    )
    return cfg
