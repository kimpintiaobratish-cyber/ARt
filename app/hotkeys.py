from __future__ import annotations

from typing import Callable, Optional


class HotkeyManager:
    def __init__(self):
        self._keyboard = None
        self._registered = False

    def register(
        self,
        on_mute: Callable[[], None],
        on_send_typed: Callable[[], None],
        on_panic: Callable[[], None],
    ) -> Optional[str]:
        try:
            import keyboard

            self._keyboard = keyboard
            keyboard.add_hotkey("ctrl+alt+m", on_mute)
            keyboard.add_hotkey("ctrl+alt+s", on_send_typed)
            keyboard.add_hotkey("ctrl+alt+p", on_panic)
            self._registered = True
            return None
        except Exception as exc:
            return f"Hotkeys disabled: {type(exc).__name__}"

    def unregister(self) -> None:
        if self._registered and self._keyboard is not None:
            self._keyboard.clear_all_hotkeys()
            self._registered = False
