"""examples/extension-hook/solution/hook_runner.py - Эталонный исполнитель хуков."""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict, List, Optional


class HookRunner:
    """Исполнитель и валидатор хуков расширений Codex CLI."""

    ALLOWED_EVENTS = {"pre-command", "post-command", "pre-commit"}
    BLOCKED_PATTERNS = ["curl", "wget", "rm -rf", "format ", "powershell -enc", "bash -c"]

    def execute_hook(self, hook_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        event = hook_config.get("event")
        if event not in self.ALLOWED_EVENTS:
            return {
                "success": False,
                "status": "rejected",
                "error": f"Неизвестное событие хука: '{event}'. Разрешены: {sorted(list(self.ALLOWED_EVENTS))}",
            }

        command = hook_config.get("command")
        if not command or not isinstance(command, list):
            return {
                "success": False,
                "status": "rejected",
                "error": "Параметр command должен быть непустым списком аргументов",
            }

        cmd_str = " ".join(str(c) for c in command).lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in cmd_str:
                return {
                    "success": False,
                    "status": "rejected",
                    "error": f"Обнаружена потенциально опасная инструкция в команде хука: '{pattern}'",
                }

        # Запуск команды хука
        try:
            res = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return {
                    "success": True,
                    "status": "executed",
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "error": f"Хук завершился с кодом ошибки {res.returncode}: {res.stderr.strip()}",
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "status": "failed",
                "error": "Превышен таймаут выполнения хука",
            }
        except Exception as e:
            return {
                "success": False,
                "status": "failed",
                "error": f"Ошибка выполнения хука: {e}",
            }
