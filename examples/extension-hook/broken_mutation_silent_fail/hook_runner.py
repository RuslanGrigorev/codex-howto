"""examples/extension-hook/broken_mutation_silent_fail/hook_runner.py - Ошибочная мутация."""

from __future__ import annotations
from typing import Any, Dict


class HookRunner:
    """Ошибочная мутация: подавляет ошибки выполнения, всегда возвращая success=True."""

    def execute_hook(self, hook_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        event = hook_config.get("event")
        if event not in {"pre-command", "post-command", "pre-commit"}:
            return {"success": False, "status": "rejected", "error": "Неизвестное событие"}

        cmd = hook_config.get("command", [])
        cmd_str = " ".join(str(c) for c in cmd).lower()
        if any(p in cmd_str for p in ["curl", "rm -rf", "format "]):
            return {"success": False, "status": "rejected", "error": "Опасная команда"}

        # Ошибка: всегда success=True, даже если команда упала
        return {"success": True, "status": "executed", "error": None}
