from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import ctypes
import ctypes.wintypes

import mss
from PIL import Image


@dataclass
class ScreenshotResult:
    png_bytes: bytes
    preview_image: Image.Image
    timestamp: str
    capture_mode: str


class ScreenshotService:
    def __init__(self, data_dir: Path, save_screenshots: bool = False):
        self.data_dir = data_dir
        self.save_screenshots = save_screenshots
        self.last_result: ScreenshotResult | None = None
        self.screens_dir = self.data_dir / "screenshots"
        self.screens_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, mode: str = "active_window") -> ScreenshotResult:
        with mss.mss() as sct:
            mon = self._active_monitor(sct) if mode == "active_window" else sct.monitors[1]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.rgb)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bio = BytesIO()
        img.save(bio, format="PNG")
        png_data = bio.getvalue()
        preview = img.copy()
        preview.thumbnail((240, 140))
        result = ScreenshotResult(
            png_bytes=png_data,
            preview_image=preview,
            timestamp=ts,
            capture_mode=mode,
        )
        self.last_result = result

        if self.save_screenshots:
            path = self.screens_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img.save(path)
        return result

    def _active_monitor(self, sct: mss.mss) -> dict:
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            rect = ctypes.wintypes.RECT()
            if hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                x, y = rect.left, rect.top
                for mon in sct.monitors[1:]:
                    if mon["left"] <= x < mon["left"] + mon["width"] and mon["top"] <= y < mon["top"] + mon["height"]:
                        return mon
        except Exception:
            pass
        return sct.monitors[1]
