from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Callable, Optional

import sounddevice as sd
import webrtcvad


@dataclass
class VoiceEvent:
    text: str
    raw_text: str


class AlwaysOnAudioListener:
    """Always-on listener: every valid speech segment becomes a command.

    No wake phrase required.
    """

    def __init__(
        self,
        stt,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        vad_level: int = 2,
    ):
        self.stt = stt
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.frame_samples = int(sample_rate * frame_ms / 1000)
        self.frame_bytes = self.frame_samples * 2
        self.vad = webrtcvad.Vad(vad_level)
        self._audio_q: queue.Queue[bytes] = queue.Queue(maxsize=400)
        self._running = False
        self._muted = False
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        self.on_command: Optional[Callable[[VoiceEvent], None]] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stream = sd.RawInputStream(
            channels=1,
            samplerate=self.sample_rate,
            dtype="int16",
            blocksize=self.frame_samples,
            callback=self._audio_callback,
        )
        self._stream.start()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def set_muted(self, value: bool) -> None:
        self._muted = value

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if not self._running or self._muted:
            return
        try:
            self._audio_q.put_nowait(bytes(indata))
        except queue.Full:
            pass

    def _worker_loop(self) -> None:
        speech_buf = bytearray()
        silence_frames = 0
        min_speech_frames = 8
        max_pause_frames = 20

        while self._running:
            try:
                frame = self._audio_q.get(timeout=0.2)
            except queue.Empty:
                continue
            if len(frame) != self.frame_bytes:
                continue

            is_speech = self.vad.is_speech(frame, self.sample_rate)
            if is_speech:
                speech_buf.extend(frame)
                silence_frames = 0
            elif speech_buf:
                silence_frames += 1
                if silence_frames <= max_pause_frames:
                    speech_buf.extend(frame)
                else:
                    self._flush_segment(bytes(speech_buf), min_speech_frames)
                    speech_buf.clear()
                    silence_frames = 0

    def _flush_segment(self, segment: bytes, min_speech_frames: int) -> None:
        if len(segment) < min_speech_frames * self.frame_bytes:
            return
        text = self.stt.transcribe_pcm16(segment, self.sample_rate).strip()
        if not text:
            return
        if len(text) < 2:
            return
        self._emit_command(text, text)

    def _emit_command(self, clean_text: str, raw_text: str) -> None:
        if self.on_command:
            self.on_command(VoiceEvent(text=clean_text, raw_text=raw_text))
