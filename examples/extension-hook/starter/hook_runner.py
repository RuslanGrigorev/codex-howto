"""examples/extension-hook/starter/hook_runner.py - Заготовка для упражнения."""

from __future__ import annotations
from typing import Any, Dict


class HookRunner:
    """Исполнитель и валидатор хуков расширений Codex CLI."""

    def execute_hook(self, hook_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Реализовать проверку разрешенных событий, блокировку опасных инструкций
        # и выполнение безопасных локальных хуков
        raise NotImplementedError("execute_hook не реализован")
