#!/usr/bin/env python3
"""Надёжный потоковый парсер событий JSONL для codex exec (ADR-CD-04, Finding 8).

Обрабатывает:
- Успешные потоки с терминальными событиями (turn_complete, session_closed).
- Оборванные и незавершённые потоки (truncated streams).
- События сбоя (turn.failed, error).
- События повторных попыток (retry events).
- Некорректные строки (malformed JSON) с изоляцией ошибок.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

# UTF-8 reconfigure
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


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


def main():
    sample_file = Path(__file__).parent / "sample_output.jsonl"
    parser = JSONLStreamParser()
    summary = parser.parse_stream(sample_file.read_text(encoding="utf-8").splitlines())

    assert summary.is_completed is True
    assert len(summary.tool_calls) > 0
    print(f"Успешно обработано {summary.valid_events} событий потока (инструментов: {len(summary.tool_calls)})")
    print("PASS: A01 batch exec jsonl stream parsed")


if __name__ == "__main__":
    main()
