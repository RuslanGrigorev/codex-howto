"""examples/session-restore/broken_mutation_lost_history/session_manager.py - Ошибочная мутация."""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class SessionManager:
    """Ошибочная реализация: теряет историю сообщений при вызове resume."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, title: str) -> Dict[str, Any]:
        session = {"id": session_id, "title": title, "messages": []}
        self._sessions[session_id] = session
        return dict(session)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["messages"].append({"role": role, "content": content})

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        # Ошибка: всегда возвращает пустой список сообщений (потеря контекста)
        if session_id not in self._sessions:
            raise KeyError(f"Сессия {session_id} не найдена")
        return {
            "id": self._sessions[session_id]["id"],
            "title": self._sessions[session_id]["title"],
            "messages": [],
        }

    def clear_session_context(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["messages"].clear()

    def list_sessions(self) -> List[Dict[str, Any]]:
        return []

    def check_workspace_divergence(
        self,
        session_id: str,
        tracked_files: Dict[str, str],
        current_files: Dict[str, str],
    ) -> Dict[str, Any]:
        return {"diverged": True, "added": ["new_file.py"], "removed": ["utils.py"], "modified": ["main.py"]}
