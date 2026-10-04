"""examples/cli-stream/broken_mutation_single_json/stream_parser.py - Ошибочная мутация."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable


class CodexStreamParser:
    """Ошибочная мутация: пытается прочитать весь ввод как один монолитный JSON объект вместо JSONL."""

    def parse_stream(self, stream_lines: Iterable[str]) -> Dict[str, Any]:
        full_text = "\n".join(stream_lines)
        try:
            # Ошибка: JSONL поток из нескольких строк не является валидным монолитным JSON!
            data = json.loads(full_text)
            return {"success": True, "exit_code": 0, "output_text": "", "events_count": 1, "errors": []}
        except Exception:
            return {"success": False, "exit_code": 1, "output_text": "", "events_count": 0, "errors": ["Failed monolithic JSON"]}
