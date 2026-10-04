"""examples/session-restore/starter/session_manager.py - Заготовка для упражнения."""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class SessionManager:
    """Менеджер сессий Codex CLI, обеспечивающий разделение состояния диалога и файлового дерева."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, title: str) -> Dict[str, Any]:
        # TODO: Реализовать создание структуры сессии
        raise NotImplementedError("create_session не реализован")

    def add_message(self, session_id: str, role: str, content: str) -> None:
        # TODO: Реализовать добавление сообщения в историю
        raise NotImplementedError("add_message не реализован")

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        # TODO: Реализовать возобновление сессии с возвратом истории
        raise NotImplementedError("resume_session не реализован")

    def clear_session_context(self, session_id: str) -> None:
        # TODO: Реализовать очистку контекста сессии без вмешательства в файлы
        raise NotImplementedError("clear_session_context не реализован")

    def list_sessions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("list_sessions не реализован")

    def check_workspace_divergence(
        self,
        session_id: str,
        tracked_files: Dict[str, str],
        current_files: Dict[str, str],
    ) -> Dict[str, Any]:
        # TODO: Реализовать сравнение файлового состояния
        raise NotImplementedError("check_workspace_divergence не реализован")
