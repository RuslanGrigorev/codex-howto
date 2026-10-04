"""examples/extension-hook/broken_mutation_allow_insecure/hook_runner.py - Ошибочная мутация."""

from __future__ import annotations
from typing import Any, Dict


class HookRunner:
    """Ошибочная мутация: не фильтрует опасные команды (пропускает curl, rm -rf и т.д.)."""

    def execute_hook(self, hook_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        event = hook_config.get("event")
        if event not in {"pre-command", "post-command", "pre-commit"}:
            return {"success": False, "status": "rejected", "error": "Неизвестное событие"}

        # Ошибка: считает любую опасную команду безопасной и выполненной
        return {"success": True, "status": "executed", "error": None}
