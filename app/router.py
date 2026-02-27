from __future__ import annotations

from dataclasses import dataclass


TEXT_MODEL_DEFAULT = "stepfun-ai/step-3.5-flash"
TEXT_MODEL_CODER = "qwen/qwen3-coder:free"
VISION_MODEL = "qwen/qwen3-vl-30b-a3b-thinking:free"


@dataclass
class RoutingDecision:
    model: str
    include_image: bool


CODER_HINTS = {
    "исправь",
    "почини",
    "рефактор",
    "напиши код",
    "go",
    "ошибка компиляции",
}
SCREEN_HINTS = {"по экрану", "на экране", "в окне", "смотри", "что на скрине"}


def _is_coder_intent(text: str, force_fix: bool = False) -> bool:
    if force_fix:
        return True
    txt = text.lower()
    return any(h in txt for h in CODER_HINTS)


def pick_route(text: str, vision_mode: str = "AUTO", force_fix: bool = False) -> RoutingDecision:
    txt = text.strip().lower()
    is_coder = _is_coder_intent(txt, force_fix=force_fix)
    vision_mode = vision_mode.upper()

    if vision_mode == "OFF":
        return RoutingDecision(model=TEXT_MODEL_CODER if is_coder else TEXT_MODEL_DEFAULT, include_image=False)

    if vision_mode == "ON":
        return RoutingDecision(model=VISION_MODEL, include_image=True)

    short_without_screen_need = len(txt) < 50 and not any(k in txt for k in SCREEN_HINTS)
    if short_without_screen_need and not is_coder:
        return RoutingDecision(model=TEXT_MODEL_DEFAULT, include_image=False)

    if is_coder and short_without_screen_need:
        return RoutingDecision(model=TEXT_MODEL_CODER, include_image=False)

    return RoutingDecision(model=VISION_MODEL, include_image=True)
