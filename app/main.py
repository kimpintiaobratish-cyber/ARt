from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .audio_listener import AlwaysOnAudioListener
from .config import DB_PATH, DATA_DIR, load_config
from .hotkeys import HotkeyManager
from .llm_openrouter import OpenRouterClient
from .memory_sqlite import MemoryStore
from .screenshot import ScreenshotService
from .stt_whisper import WhisperSTT
from .tts_piper import PiperTTS
from .ui import TutorWindow


def main() -> int:
    cfg = load_config()

    app = QApplication(sys.argv)

    memory = MemoryStore(DB_PATH)
    stt = WhisperSTT(cfg.whisper_model)
    audio_listener = AlwaysOnAudioListener(stt=stt)
    screenshot_service = ScreenshotService(DATA_DIR, save_screenshots=cfg.save_screenshots)
    llm = OpenRouterClient(
        api_key=cfg.openrouter_api_key,
        base_url=cfg.openrouter_base_url,
        referer=cfg.openrouter_http_referer,
        app_title=cfg.openrouter_app_title,
    )
    tts = PiperTTS(cfg.piper_binary, cfg.piper_model_path)
    hotkeys = HotkeyManager()

    window = TutorWindow(
        memory=memory,
        screenshot_service=screenshot_service,
        llm=llm,
        tts=tts,
        audio_listener=audio_listener,
        hotkeys=hotkeys,
        initial_vision_mode=cfg.vision_mode,
        capture_mode=cfg.default_capture_mode,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
