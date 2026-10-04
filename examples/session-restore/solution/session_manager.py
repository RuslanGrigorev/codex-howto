"""examples/session-restore/solution/session_manager.py - Эталонное решение."""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class SessionManager:
    """Менеджер сессий Codex CLI, обеспечивающий разделение состояния диалога и файлового дерева."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, title: str) -> Dict[str, Any]:
        """Создает новую сессию с пустым списком сообщений."""
        session = {
            "id": session_id,
            "title": title,
            "messages": [],
        }
        self._sessions[session_id] = session
        return dict(session)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Добавляет сообщение в историю сессии."""
        if session_id not in self._sessions:
            raise KeyError(f"Сессия {session_id} не найдена")
        self._sessions[session_id]["messages"].append({
            "role": role,
            "content": content,
        })

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Возобновляет и возвращает сессию с ее полной историей."""
        if session_id not in self._sessions:
            raise KeyError(f"Сессия {session_id} не найдена")
        return {
            "id": self._sessions[session_id]["id"],
            "title": self._sessions[session_id]["title"],
            "messages": list(self._sessions[session_id]["messages"]),
        }

    def clear_session_context(self, session_id: str) -> None:
        """Очищает контекст сообщений в сессии, не затрагивая внешние файлы."""
        if session_id in self._sessions:
            self._sessions[session_id]["messages"].clear()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Возвращает список всех зарегистрированных сессий."""
        return [
            {
                "id": s["id"],
                "title": s["title"],
                "message_count": len(s["messages"]),
            }
            for s in self._sessions.values()
        ]

    def check_workspace_divergence(
        self,
        session_id: str,
        tracked_files: Dict[str, str],
        current_files: Dict[str, str],
    ) -> Dict[str, Any]:
        """Сравнивает состояние файлов на диске с зафиксированным снимком.

        Не изменяет сессию и не модифицирует переданные словари.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Сессия {session_id} не найдена")

        tracked_keys = set(tracked_files.keys())
        current_keys = set(current_files.keys())

        added = sorted(list(current_keys - tracked_keys))
        removed = sorted(list(tracked_keys - current_keys))
        modified = sorted([
            k for k in (tracked_keys & current_keys)
            if tracked_files[k] != current_files[k]
        ])

        diverged = bool(added or removed or modified)
        return {
            "diverged": diverged,
            "added": added,
            "removed": removed,
            "modified": modified,
        }
