"""examples/cli-stream/solution/stream_parser.py - Эталонный парсер потока JSONL."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List


class CodexStreamParser:
    """Парсер потокового вывода Codex CLI (--stream-json) в формате JSON Lines."""

    def parse_stream(self, stream_lines: Iterable[str]) -> Dict[str, Any]:
        events_count = 0
        output_chunks: List[str] = []
        errors: List[str] = []
        exit_code = 0
        has_error = False

        for raw_line in stream_lines:
            line = raw_line.strip()
            if not line:
                continue

            # Проверка на валидный единичный JSON объект в строке
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Невалидный JSON в строке: {e}")
                has_error = True
                continue

            if not isinstance(event, dict):
                errors.append("Строка потока не является JSON-объектом")
                has_error = True
                continue

            events_count += 1
            event_type = event.get("type")

            if event_type == "item_delta":
                output_chunks.append(str(event.get("delta", "")))
            elif event_type == "error":
                has_error = True
                msg = event.get("message", "Неизвестная ошибка")
                code = event.get("code")
                errors.append(f"{msg} (код {code})" if code else msg)
            elif event_type == "done":
                exit_code = int(event.get("exit_code", 0))
                if exit_code != 0:
                    has_error = True

        if exit_code != 0:
            has_error = True

        return {
            "success": not has_error and len(errors) == 0 and exit_code == 0,
            "exit_code": exit_code,
            "output_text": "".join(output_chunks),
            "events_count": events_count,
            "errors": errors,
        }
