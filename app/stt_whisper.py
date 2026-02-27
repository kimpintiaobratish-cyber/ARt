from __future__ import annotations

from faster_whisper import WhisperModel
import numpy as np


class WhisperSTT:
    def __init__(self, model_name: str = "small"):
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def transcribe_pcm16(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self.model.transcribe(audio, language="ru", vad_filter=True, beam_size=1)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text
