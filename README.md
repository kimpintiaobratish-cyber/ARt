# Always-On Coding Tutor (Auto-Screenshot) — MVP

Локальный desktop-ассистент под **Windows 10/11** для обучения программированию:
- всегда слушает микрофон локально;
- слушает речь без wake-фразы (сразу обрабатывает голосовые реплики);
- **перед каждым запросом в LLM делает автоскриншот**;
- отправляет текст + (по режиму Vision) скриншот в OpenRouter;
- показывает ответ в UI и может озвучивать через Piper;
- ведёт память в SQLite и поддерживает `/summary`, `/quiz`.

## Структура

```text
/app
  main.py
  ui.py
  audio_listener.py
  stt_whisper.py
  tts_piper.py
  screenshot.py
  llm_openrouter.py
  memory_sqlite.py
  router.py
  prompts.py
  config.py
  hotkeys.py
/data
.env.example
requirements.txt
README.md
```

## Безопасность и контроль

- Микрофон always-on: каждая завершённая голосовая реплика автоматически отправляется в LLM.
- Текст вручную отправляется только через `Send` / `Fix Code`.
- Автоскриншот делается **только перед отправкой в LLM**.
- В UI всегда виден preview последнего скрина + timestamp.
- `Panic` мгновенно глушит микрофон и блокирует отправку.
- Hotkeys:
  - `Ctrl+Alt+M` — Mute mic
  - `Ctrl+Alt+S` — Send typed
  - `Ctrl+Alt+P` — Panic toggle
- API-ключ не логируется.
- Скриншоты в RAM по умолчанию. На диск — только при `SAVE_SCREENSHOTS=true`.

## Установка

### 1) Python и зависимости

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Настройка `.env`

```bash
copy .env.example .env
```

Заполните:
- `OPENROUTER_API_KEY`
- `PIPER_MODEL_PATH` (если используете озвучку)

### 3) Установка Piper

1. Скачайте бинарник Piper для Windows и добавьте в PATH
   **или** пропишите полный путь в `PIPER_BINARY`.
2. Скачайте ONNX-голос (например ru_RU) и укажите путь в `PIPER_MODEL_PATH`.

> Если Piper не настроен, UI продолжит работать, но без озвучки.

### 4) Запуск

```bash
python -m app.main
```

## Как работает маршрутизация моделей

- Базовая текстовая: **Step 3.5 Flash**.
- Если в запросе есть намерение фикса кода (`исправь`, `почини`, `рефактор`, `напиши код`, `go`, `ошибка компиляции`) или нажат `Fix Code` → **Qwen3 Coder**.
- Vision-модель: **Qwen3 VL 30B A3B Thinking**.

Режим `Vision mode`:
- `AUTO` (по умолчанию): короткие запросы без привязки к экрану могут уйти без картинки.
- `ON`: всегда отправлять скрин в vision-модель.
- `OFF`: не отправлять картинки.

> Важно: скриншот всё равно создаётся перед каждым LLM-запросом (для UI preview и соблюдения политики).

## Active window capture

В MVP используется определение монитора активного окна через WinAPI (`GetForegroundWindow` + `GetWindowRect`) и захват монитора через `mss`.
- Если определение активного окна нестабильно или недоступно, автоматически включается fallback на полный экран.
- Точное crop окна в этом MVP не делается (только монитор/полный экран).

## Команды памяти

- `/summary` — краткая сводка по истории SQLite
- `/quiz` — мини-квиз по последним обсуждениям

## Ограничения MVP

- Wake-word не используется: любые распознанные голосовые фразы отправляются как запросы (если не включён Mute/Panic).
- Для глобальных hotkeys на некоторых системах могут потребоваться повышенные права.
