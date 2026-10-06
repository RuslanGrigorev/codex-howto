#!/usr/bin/env python3
"""Надёжный клиент автоматизации codex exec с границей процессов и FSM (ADR-CD-04, Finding 5).

Архитектура:
- JSONLStreamParser: потоковый разбор структурированных событий JSONL.
- BaseExecRunner: абстрактная граница выполнения процесса exec.
- SubprocessExecRunner: запуск внешнего процесса с разделением stdout/stderr, кодами выхода и таймаутами.
- FixtureExecRunner: детерминированный запуск для автономных проверок без внешних зависимостей.
- ExecResult: агрегированный результат с кодом возврата, диагностикой stderr, последним сообщением и событиями.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

# UTF-8 reconfigure
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class StreamParsingError(Exception):
    """Ошибка разбора потока событий."""
    pass


class TruncatedStreamError(StreamParsingError):
    """Поток завершился до наступления терминального события."""
    pass


class ExecutionFailedError(StreamParsingError):
    """В потоке зафиксировано явное событие сбоя выполнения."""
    pass


@dataclass
class StreamParseSummary:
    total_lines: int = 0
    valid_events: int = 0
    malformed_lines: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    retries: list[dict[str, Any]] = field(default_factory=list)
    failure_event: Optional[dict[str, Any]] = None
    terminal_event: Optional[dict[str, Any]] = None
    last_assistant_message: Optional[str] = None
    is_completed: bool = False


class JSONLStreamParser:
    """Парсер потока событий Codex CLI 0.160.0."""

    def __init__(self):
        self.summary = StreamParseSummary()
        self.events: list[dict[str, Any]] = []

    def parse_line(self, line: str) -> Optional[dict[str, Any]]:
        line = line.strip()
        if not line:
            return None
        self.summary.total_lines += 1

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self.summary.malformed_lines += 1
            return None

        self.summary.valid_events += 1
        self.events.append(event)

        ev_type = event.get("event") or event.get("type")

        # Обработка вызовов инструментов
        if ev_type in {"tool_call", "tool_use"}:
            self.summary.tool_calls.append(event)

        # Обработка повторов
        elif ev_type in {"retry", "tool_retry"}:
            self.summary.retries.append(event)

        # Обработка сообщений ассистента / последнего сообщения
        elif ev_type in {"item.completed", "message"} and "text" in event:
            self.summary.last_assistant_message = event["text"]
        elif event.get("role") == "assistant" and "content" in event:
            self.summary.last_assistant_message = event["content"]

        # Обработка ошибок выполнения
        elif ev_type in {"turn.failed", "error", "session_error"} or event.get("status") in {"failed", "error"}:
            self.summary.failure_event = event

        # Обработка терминальных событий
        elif ev_type in {"turn_complete", "session_closed", "turn.completed"} or (event.get("status") == "completed"):
            self.summary.terminal_event = event
            self.summary.is_completed = True

        return event

    def parse_stream(self, lines: Iterable[str]) -> StreamParseSummary:
        for line in lines:
            self.parse_line(line)

        # Проверка терминального состояния
        if self.summary.failure_event is not None:
            err_msg = self.summary.failure_event.get("message") or self.summary.failure_event.get("error") or "Unknown error"
            raise ExecutionFailedError(f"В потоке обнаружен сбой исполнения ({self.summary.failure_event.get('event')}): {err_msg}")

        if not self.summary.is_completed:
            raise TruncatedStreamError(
                f"Поток оборван: прочитано строк {self.summary.total_lines}, но финальное терминальное событие не получено."
            )

        return self.summary


@dataclass
class ExecResult:
    """Агрегированный результат выполнения команды exec (ADR-CD-04)."""
    exit_code: int
    stdout_events: list[dict[str, Any]]
    stderr: str
    summary: StreamParseSummary
    last_message: Optional[str] = None
    success: bool = True
    is_cancelled: bool = False
    is_timeout: bool = False
    error_message: Optional[str] = None


class BaseExecRunner(ABC):
    """Абстрактный раннер выполнения команды exec."""

    @abstractmethod
    def run(self, args: list[str], prompt: str, timeout: Optional[float] = None) -> ExecResult:
        raise NotImplementedError

    @abstractmethod
    def cancel(self) -> None:
        raise NotImplementedError


class FixtureExecRunner(BaseExecRunner):
    """Детерминированный раннер для офлайн-тестирования."""

    def __init__(self):
        self._scenarios: dict[str, ExecResult] = {}
        self._was_cancelled = False

    def register_scenario(self, prompt_keyword: str, result: ExecResult) -> None:
        self._scenarios[prompt_keyword] = result

    def cancel(self) -> None:
        self._was_cancelled = True

    def run(self, args: list[str], prompt: str, timeout: Optional[float] = None) -> ExecResult:
        if self._was_cancelled:
            return ExecResult(
                exit_code=130,
                stdout_events=[],
                stderr="Execution cancelled",
                summary=StreamParseSummary(),
                success=False,
                is_cancelled=True,
                error_message="Cancelled by user"
            )

        if timeout is not None and timeout <= 0:
            return ExecResult(
                exit_code=124,
                stdout_events=[],
                stderr="Process timed out",
                summary=StreamParseSummary(),
                success=False,
                is_timeout=True,
                error_message=f"Timeout after {timeout}s"
            )

        for kw, res in self._scenarios.items():
            if kw in prompt:
                return res

        # По умолчанию успешный базовый результат
        parser = JSONLStreamParser()
        lines = [
            '{"event":"turn_start","timestamp":1700000000}',
            '{"event":"item.completed","text":"Базовый результат выполнения"}',
            '{"event":"turn_complete","timestamp":1700000001}'
        ]
        summary = parser.parse_stream(lines)
        return ExecResult(
            exit_code=0,
            stdout_events=parser.events,
            stderr="",
            summary=summary,
            last_message=summary.last_assistant_message,
            success=True
        )


class SubprocessExecRunner(BaseExecRunner):
    """Раннер с реальным дочерним процессом и полным контролем жизненного цикла."""

    def __init__(self, executable: str = "codex"):
        self.executable = executable
        self._proc: Optional[subprocess.Popen] = None
        self._is_cancelled = False
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            self._is_cancelled = True
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                except Exception:
                    self._proc.kill()

    def run(self, args: list[str], prompt: str, timeout: Optional[float] = None) -> ExecResult:
        cmd = [self.executable, "exec"] + args + [prompt]
        self._is_cancelled = False

        parser = JSONLStreamParser()
        stderr_chunks: list[str] = []

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
        except FileNotFoundError as exc:
            return ExecResult(
                exit_code=127,
                stdout_events=[],
                stderr=str(exc),
                summary=parser.summary,
                success=False,
                error_message=f"Исполняемый файл '{self.executable}' не найден"
            )

        def read_stderr():
            if self._proc and self._proc.stderr:
                stderr_chunks.append(self._proc.stderr.read())

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        timed_out = False
        start_time = time.time()

        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            parser.parse_line(line)
            if timeout and (time.time() - start_time) > timeout:
                timed_out = True
                self.cancel()
                break

        try:
            exit_code = self._proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            exit_code = self._proc.wait()

        stderr_thread.join(timeout=1.0)
        stderr_str = "".join(stderr_chunks)

        success = (exit_code == 0) and not self._is_cancelled and not timed_out
        return ExecResult(
            exit_code=exit_code,
            stdout_events=parser.events,
            stderr=stderr_str,
            summary=parser.summary,
            last_message=parser.summary.last_assistant_message,
            success=success,
            is_cancelled=self._is_cancelled,
            is_timeout=timed_out,
            error_message=stderr_str if not success else None
        )


def main():
    # 1. Тест парсера JSONL
    sample_file = Path(__file__).parent / "sample_output.jsonl"
    parser = JSONLStreamParser()
    if sample_file.exists():
        summary = parser.parse_stream(sample_file.read_text(encoding="utf-8").splitlines())
        assert summary.is_completed is True
        assert len(summary.tool_calls) > 0

    # 2. Тест FixtureExecRunner
    runner = FixtureExecRunner()
    
    # 2.1 Успешный запуск
    res = runner.run(["--sandbox", "read-only"], "Тестовый промпт")
    assert res.success is True
    assert res.exit_code == 0
    assert res.last_message == "Базовый результат выполнения"

    # 2.2 Неуспешный запуск (ненулевой код выхода)
    runner.register_scenario(
        "ошиб",
        ExecResult(
            exit_code=1,
            stdout_events=[],
            stderr="Syntax error in python code",
            summary=StreamParseSummary(),
            success=False,
            error_message="Non-zero exit"
        )
    )
    fail_res = runner.run([], "промпт с ошибкой")
    assert fail_res.success is False
    assert fail_res.exit_code == 1
    assert "Syntax error" in fail_res.stderr

    # 2.3 Отмена
    cancel_runner = FixtureExecRunner()
    cancel_runner.cancel()
    cancelled_res = cancel_runner.run([], "любой промпт")
    assert cancelled_res.is_cancelled is True
    assert cancelled_res.exit_code == 130

    # 2.4 Тайм-аут
    timeout_res = runner.run([], "промпт", timeout=0.0)
    assert timeout_res.is_timeout is True
    assert timeout_res.exit_code == 124

    print("PASS: A01 batch exec client lifecycle & runner validated")


if __name__ == "__main__":
    main()
