#!/usr/bin/env python3
"""Учебный программный SDK-клиент для вызова Codex CLI с разделением транспорта."""
from __future__ import annotations
import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

@dataclass
class CodexResult:
    exit_code: int
    output: str
    events: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    refusal: Optional[str] = None
    error_message: Optional[str] = None

class CodexSDKError(Exception):
    """Базовое исключение SDK клиента."""
    pass

class CodexTimeoutError(CodexSDKError):
    """Исключение при превышении тайм-аута сессии."""
    pass

class CodexExecutionError(CodexSDKError):
    """Исключение при сбое выполнения команды или отказе модели."""
    pass

class BaseSDKTransport(ABC):
    """Абстрактный интерфейс транспорта для взаимодействия с Codex CLI."""

    @abstractmethod
    def execute(
        self,
        command: list[str],
        cwd: Path,
        env: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> CodexResult:
        """Выполняет вызов Codex CLI и возвращает структурированный результат."""
        raise NotImplementedError

class SubprocessSDKTransport(BaseSDKTransport):
    """Производственный транспорт на базе вызова подпроцесса."""

    def execute(
        self,
        command: list[str],
        cwd: Path,
        env: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> CodexResult:
        try:
            proc = subprocess.run(
                command,
                cwd=str(cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8"
            )
            events = []
            refusal = None
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        ev = json.loads(line)
                        events.append(ev)
                        if ev.get("type") == "refusal" or ev.get("refusal"):
                            refusal = ev.get("message") or ev.get("refusal")
                    except json.JSONDecodeError:
                        pass

            success = proc.returncode == 0 and refusal is None
            return CodexResult(
                exit_code=proc.returncode,
                output=proc.stdout,
                events=events,
                success=success,
                refusal=refusal,
                error_message=proc.stderr if proc.returncode != 0 else None
            )
        except subprocess.TimeoutExpired as exc:
            raise CodexTimeoutError(f"Превышен таймаут выполнения Codex CLI ({timeout}s)") from exc
        except FileNotFoundError as exc:
            raise CodexExecutionError("Исполняемый файл Codex CLI не найден в системе") from exc

class FixtureSDKTransport(BaseSDKTransport):
    """Детерминированный тестовый транспорт для офлайн-проверок и тестов."""

    def __init__(self, canned_responses: Optional[dict[str, CodexResult]] = None):
        self.canned_responses = canned_responses or {}
        self.call_history: list[dict[str, Any]] = []

    def register_response(self, prompt_substring: str, result: CodexResult) -> None:
        self.canned_responses[prompt_substring] = result

    def execute(
        self,
        command: list[str],
        cwd: Path,
        env: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> CodexResult:
        self.call_history.append({"command": command, "cwd": cwd, "timeout": timeout})
        cmd_str = " ".join(command)
        for sub, res in self.canned_responses.items():
            if sub in cmd_str:
                return res

        return CodexResult(
            exit_code=0,
            output=f"Executed: {cmd_str}",
            events=[{"event": "completed", "command": command}],
            success=True
        )

class CodexSDKClient:
    """Программный клиент для автоматизации Codex CLI 0.160.0."""

    def __init__(
        self,
        workspace: Path,
        sandbox_mode: str = "workspace-write",
        approval_policy: str = "never",
        transport: Optional[BaseSDKTransport] = None,
        default_timeout: float = 60.0
    ):
        self.workspace = Path(workspace).resolve()
        self.sandbox_mode = sandbox_mode
        self.approval_policy = approval_policy
        self.transport = transport or SubprocessSDKTransport()
        self.default_timeout = default_timeout

    def run_prompt(
        self,
        prompt: str,
        approval_policy: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> CodexResult:
        """Выполняет промпт через exec-режим Codex CLI."""
        policy = approval_policy or self.approval_policy
        tout = timeout or self.default_timeout

        cmd = [
            "codex", "exec",
            "--approval-policy", policy,
            "--sandbox-mode", self.sandbox_mode,
            "--jsonl",
            prompt
        ]

        result = self.transport.execute(cmd, cwd=self.workspace, timeout=tout)

        if not result.success:
            if result.refusal:
                raise CodexExecutionError(f"Модель отклонила запрос: {result.refusal}")
            if result.exit_code != 0:
                raise CodexExecutionError(f"Сбой выполнения (код {result.exit_code}): {result.error_message}")

        return result

def main():
    fixture = FixtureSDKTransport()
    client = CodexSDKClient(Path("."), transport=fixture)
    res = client.run_prompt("Проверь синтаксис")
    assert res.success, "Ошибка вызова клиента"
    print("PASS: A03 Python SDK client validated")

if __name__ == "__main__":
    main()
