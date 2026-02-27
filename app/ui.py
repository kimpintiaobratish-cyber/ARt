from __future__ import annotations

import queue
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .audio_listener import AlwaysOnAudioListener, VoiceEvent
from .llm_openrouter import OpenRouterClient
from .memory_sqlite import MemoryStore
from .prompts import SYSTEM_PROMPT
from .router import pick_route
from .screenshot import ScreenshotService
from .tts_piper import PiperTTS


@dataclass
class RequestTask:
    text: str
    source: str
    force_fix: bool = False


class TutorWindow(QMainWindow):
    def __init__(
        self,
        memory: MemoryStore,
        screenshot_service: ScreenshotService,
        llm: OpenRouterClient,
        tts: PiperTTS,
        audio_listener: AlwaysOnAudioListener,
        hotkeys,
        initial_vision_mode: str,
        capture_mode: str,
    ):
        super().__init__()
        self.setWindowTitle("Always-On Coding Tutor")
        self.resize(980, 720)

        self.memory = memory
        self.screenshot_service = screenshot_service
        self.llm = llm
        self.tts = tts
        self.audio_listener = audio_listener
        self.hotkeys = hotkeys

        self.capture_mode = capture_mode
        self.vision_mode = initial_vision_mode
        self.speak_enabled = False
        self.mic_muted = False
        self.panic_mode = False

        self.events_q: queue.Queue[VoiceEvent] = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=2)

        self._build_ui()
        self._wire_events()

        self.audio_listener.start()
        err = self.hotkeys.register(self.toggle_mute, self.send_typed, self.toggle_panic)
        if err:
            self._append_system(err)

        self.voice_timer = QTimer(self)
        self.voice_timer.timeout.connect(self._poll_voice_events)
        self.voice_timer.start(250)

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        self.preview_label = QLabel("No screenshot yet")
        self.preview_label.setFixedSize(260, 160)
        self.preview_label.setStyleSheet("border:1px solid #999;padding:4px;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_meta = QLabel("Timestamp: -")
        preview_box = QVBoxLayout()
        preview_box.addWidget(self.preview_label)
        preview_box.addWidget(self.preview_meta)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)

        top.addLayout(preview_box)
        top.addWidget(self.chat, stretch=1)
        layout.addLayout(top)

        self.input = QTextEdit()
        self.input.setPlaceholderText("Говорите свободно — ассистент слушает постоянно. Или введите текст вручную.")
        self.input.setFixedHeight(110)
        layout.addWidget(self.input)

        buttons = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.fix_btn = QPushButton("Fix Code")
        self.vision_btn = QPushButton(f"Vision {self.vision_mode}")
        self.speak_btn = QPushButton("Speak: OFF")
        self.mute_btn = QPushButton("Mute Mic")
        self.panic_btn = QPushButton("Panic")

        for b in [self.send_btn, self.fix_btn, self.vision_btn, self.speak_btn, self.mute_btn, self.panic_btn]:
            buttons.addWidget(b)
        layout.addLayout(buttons)

        self.status = QLabel("Ready: always listening")
        layout.addWidget(self.status)

    def _wire_events(self) -> None:
        self.send_btn.clicked.connect(self.send_typed)
        self.fix_btn.clicked.connect(lambda: self.send_typed(force_fix=True))
        self.vision_btn.clicked.connect(self.cycle_vision_mode)
        self.speak_btn.clicked.connect(self.toggle_speak)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.panic_btn.clicked.connect(self.toggle_panic)
        self.audio_listener.on_command = lambda evt: self.events_q.put(evt)

    def _poll_voice_events(self) -> None:
        while not self.events_q.empty():
            evt = self.events_q.get_nowait()
            if self.panic_mode:
                continue
            self._append_user(f"🎙 {evt.text}")
            self._submit_request(RequestTask(text=evt.text, source="voice"))

    def send_typed(self, force_fix: bool = False) -> None:
        if self.panic_mode:
            self._append_system("Panic mode активен: отправка заблокирована.")
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self._append_user(text)
        self._submit_request(RequestTask(text=text, source="typed", force_fix=force_fix))

    def _submit_request(self, task: RequestTask) -> None:
        if self.panic_mode:
            self._append_system("Panic mode активен: отправка заблокирована.")
            return
        self.status.setText("Processing...")
        future = self.executor.submit(self._handle_request_sync, task)
        future.add_done_callback(
            lambda f: QApplication.instance().postEvent(self, _FunctionEvent(lambda: self._on_result(f)))
        )

    def _handle_request_sync(self, task: RequestTask) -> tuple[str, str, str]:
        self.memory.add_message("user", task.text, task.source)

        if task.text == "/summary":
            ans = self.memory.build_summary()
            self.memory.add_message("assistant", ans, "system")
            return ans, "local", "-"
        if task.text == "/quiz":
            ans = self.memory.build_quiz()
            self.memory.add_message("assistant", ans, "system")
            return ans, "local", "-"

        shot = self.screenshot_service.capture(self.capture_mode)
        route = pick_route(task.text, vision_mode=self.vision_mode, force_fix=task.force_fix)

        memory_rows = self.memory.recent(30)
        lesson_context = self.memory.build_lesson_memory(80)
        enriched = task.text
        if lesson_context:
            enriched = (
                f"Текущий запрос:\n{task.text}\n\n"
                f"Контекст прошлых уроков (память):\n{lesson_context}\n\n"
                "Используй память, чтобы сохранять преемственность обучения."
            )

        answer = self.llm.chat(
            model=route.model,
            system_prompt=SYSTEM_PROMPT,
            user_text=enriched,
            memory_messages=memory_rows,
            image_png=shot.png_bytes if route.include_image else None,
        )
        self.memory.add_message("assistant", answer, "llm")
        self.memory.save_lesson_note(answer.splitlines()[0][:220] if answer else "Ответ получен")
        return answer, route.model, shot.timestamp

    def _on_result(self, future) -> None:
        try:
            answer, model, ts = future.result()
            self._append_assistant(answer)
            if ts != "-" and self.screenshot_service.last_result:
                self._refresh_preview()
            self.status.setText(f"Done ({model})")
            if self.speak_enabled:
                self.executor.submit(self.tts.speak, answer)
        except Exception as exc:
            self.status.setText("Error")
            self._append_system(f"Ошибка обработки: {type(exc).__name__}")

    def _refresh_preview(self) -> None:
        res = self.screenshot_service.last_result
        if not res:
            return
        bio = BytesIO()
        res.preview_image.save(bio, format="PNG")
        pix = QPixmap()
        pix.loadFromData(bio.getvalue(), "PNG")
        self.preview_label.setPixmap(pix)
        self.preview_meta.setText(f"Timestamp: {res.timestamp} | mode={res.capture_mode}")

    def cycle_vision_mode(self) -> None:
        modes = ["AUTO", "ON", "OFF"]
        idx = modes.index(self.vision_mode)
        self.vision_mode = modes[(idx + 1) % len(modes)]
        self.vision_btn.setText(f"Vision {self.vision_mode}")

    def toggle_speak(self) -> None:
        self.speak_enabled = not self.speak_enabled
        self.speak_btn.setText(f"Speak: {'ON' if self.speak_enabled else 'OFF'}")

    def toggle_mute(self) -> None:
        self.mic_muted = not self.mic_muted
        self.audio_listener.set_muted(self.mic_muted)
        self.mute_btn.setText("Unmute Mic" if self.mic_muted else "Mute Mic")

    def toggle_panic(self) -> None:
        self.panic_mode = not self.panic_mode
        if self.panic_mode:
            self.audio_listener.set_muted(True)
            self.mic_muted = True
            self.panic_btn.setText("Panic: ON")
            self.status.setText("Panic mode: mic muted + sending blocked")
        else:
            self.audio_listener.set_muted(False)
            self.mic_muted = False
            self.panic_btn.setText("Panic")
            self.status.setText("Panic mode OFF")

    def _append_user(self, text: str) -> None:
        self.chat.append(f"\n<b>You:</b> {text}")

    def _append_assistant(self, text: str) -> None:
        self.chat.append(f"<b>Tutor:</b> {text}\n")

    def _append_system(self, text: str) -> None:
        self.chat.append(f"<i>{text}</i>")

    def customEvent(self, event):
        if isinstance(event, _FunctionEvent):
            event.func()

    def closeEvent(self, event):
        self.audio_listener.stop()
        self.hotkeys.unregister()
        self.executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)


class _FunctionEvent(QEvent):
    TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, func):
        super().__init__(self.TYPE)
        self.func = func
