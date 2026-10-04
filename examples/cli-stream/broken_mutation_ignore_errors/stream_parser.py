"""examples/cli-stream/broken_mutation_ignore_errors/stream_parser.py - Ошибочная мутация."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List


class CodexStreamParser:
    """Ошибочная мутация: игнорирует события ошибок (type=error)."""

    def parse_stream(self, stream_lines: Iterable[str]) -> Dict[str, Any]:
        output_chunks: List[str] = []
        events_count = 0

        for line in stream_lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events_count += 1
                if event.get("type") == "item_delta":
                    output_chunks.append(str(event.get("delta", "")))
                # Ошибка: полностью игнорирует event.get("type") == "error"
            except Exception:
                pass

        return {
            "success": True,  # Ошибка: всегда возвращает True
            "exit_code": 0,
            "output_text": "".join(output_chunks),
            "events_count": events_count,
            "errors": [],
        }
