from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Tuple


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_message(self, role: str, content: str, source: str) -> None:
        self.conn.execute(
            "INSERT INTO messages(role, content, source, created_at) VALUES (?, ?, ?, ?)",
            (role, content, source, datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def recent(self, limit: int = 20) -> List[Tuple[str, str]]:
        cur = self.conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = cur.fetchall()
        return list(reversed(rows))

    def build_lesson_memory(self, limit: int = 80) -> str:
        rows = self.recent(limit)
        if not rows:
            return ""
        compact = []
        for role, content in rows:
            role_name = "Ученик" if role == "user" else "Учитель"
            compact.append(f"{role_name}: {content[:280]}")
        text = "\n".join(compact)
        return text[-6000:]

    def save_lesson_note(self, note: str) -> None:
        self.conn.execute(
            "INSERT INTO lesson_notes(note, created_at) VALUES (?, ?)",
            (note[:2000], datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def recent_notes(self, limit: int = 10) -> list[str]:
        cur = self.conn.execute(
            "SELECT note FROM lesson_notes ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [row[0] for row in cur.fetchall()]

    def build_summary(self, limit: int = 30) -> str:
        rows = self.recent(limit)
        if not rows:
            return "Пока в памяти нет диалога."
        user_msgs = [c for r, c in rows if r == "user"]
        tutor_msgs = [c for r, c in rows if r == "assistant"]
        notes = self.recent_notes(5)
        notes_part = "\n".join(f"- {n}" for n in notes) if notes else "- пока нет"
        return (
            f"Всего сообщений: {len(rows)}\n"
            f"Запросов пользователя: {len(user_msgs)}\n"
            f"Ответов учителя: {len(tutor_msgs)}\n"
            f"Последний запрос: {user_msgs[-1][:200] if user_msgs else '—'}\n"
            f"Заметки прошлых уроков:\n{notes_part}"
        )

    def build_quiz(self) -> str:
        rows = self.recent(24)
        concepts: list[str] = []
        for role, content in rows:
            if role == "assistant":
                for line in content.splitlines():
                    low = line.lower()
                    if "исправ" in low or "шаг" in low or "упраж" in low:
                        concepts.append(line.strip())
        seed = concepts[-1] if concepts else "циклы и условия в Python"
        return (
            "Мини-квиз:\n"
            f"1) Объясни своими словами: {seed[:110]}\n"
            "2) Напиши короткий пример кода (5-10 строк).\n"
            "3) Назови одну частую ошибку и как её избежать."
        )
