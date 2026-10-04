"""examples/session-restore/broken_mutation_mix_git/session_manager.py - Ошибочная мутация."""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class SessionManager:
    """Ошибочная реализация: нарушает изоляцию, пытаясь очистить файлы при сбросе сессии."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, title: str) -> Dict[str, Any]:
        session = {"id": session_id, "title": title, "messages": []}
        self._sessions[session_id] = session
        return session

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self._sessions[session_id]["messages"].append({"role": role, "content": content})

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        return dict(self._sessions[session_id])

    def clear_session_context(self, session_id: str) -> None:
        # Ошибка: имитирует несанкционированную очистку/откат внешних файлов проекта
        if session_id in self._sessions:
            self._sessions[session_id]["messages"].clear()
            # Пытается модифицировать внешнее окружение (в тесте вызовет несовпадение)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return []

    def check_workspace_divergence(
        self,
        session_id: str,
        tracked_files: Dict[str, str],
        current_files: Dict[str, str],
    ) -> Dict[str, Any]:
        # Ошибка: мутирует переданный словарь файлов
        current_files.clear()
        return {"diverged": False, "added": [], "removed": [], "modified": []}
