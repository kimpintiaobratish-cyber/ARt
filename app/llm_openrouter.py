from __future__ import annotations

import base64
import time
from typing import Iterable

import requests


class OpenRouterClient:
    def __init__(self, api_key: str, base_url: str, referer: str, app_title: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.referer = referer
        self.app_title = app_title

    def chat(
        self,
        model: str,
        system_prompt: str,
        user_text: str,
        memory_messages: Iterable[tuple[str, str]],
        image_png: bytes | None = None,
        timeout: int = 45,
    ) -> str:
        if not self.api_key:
            return "Ошибка: не настроен OPENROUTER_API_KEY в .env"

        messages = [{"role": "system", "content": system_prompt}]
        for role, content in memory_messages:
            if role in {"user", "assistant"}:
                messages.append({"role": role, "content": content[:3000]})

        if image_png:
            b64 = base64.b64encode(image_png).decode("ascii")
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": user_text})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.4,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.app_title,
        }

        retries = 3
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )
                if resp.status_code == 429:
                    if attempt == retries:
                        return "OpenRouter: лимит запросов (429). Попробуйте позже."
                    time.sleep(1.5 * attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except requests.Timeout:
                if attempt == retries:
                    return "OpenRouter: таймаут запроса."
                time.sleep(1.0 * attempt)
            except Exception as exc:
                if attempt == retries:
                    return f"OpenRouter error: {type(exc).__name__}"
                time.sleep(0.8 * attempt)

        return "Не удалось получить ответ от модели."
