from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path


class PiperTTS:
    def __init__(self, piper_binary: str, model_path: str):
        self.piper_binary = piper_binary
        self.model_path = model_path

    def speak(self, text: str) -> None:
        if not self.model_path:
            return
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "tts.wav"
            cmd = [
                self.piper_binary,
                "--model",
                self.model_path,
                "--output_file",
                str(wav_path),
            ]
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            self._play_wav(wav_path)

    def _play_wav(self, wav_path: Path) -> None:
        import simpleaudio  # optional runtime dependency

        with wave.open(str(wav_path), "rb") as wf:
            audio_data = wf.readframes(wf.getnframes())
            play_obj = simpleaudio.play_buffer(
                audio_data,
                wf.getnchannels(),
                wf.getsampwidth(),
                wf.getframerate(),
            )
            play_obj.wait_done()
