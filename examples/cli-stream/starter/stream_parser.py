"""examples/cli-stream/starter/stream_parser.py - Заготовка для упражнения."""

from __future__ import annotations
from typing import Any, Dict, Iterable


class CodexStreamParser:
    """Парсер потокового вывода Codex CLI (--stream-json) в формате JSON Lines."""

    def parse_stream(self, stream_lines: Iterable[str]) -> Dict[str, Any]:
        # TODO: Реализовать построчную обработку JSONL потока,
        # сборку текста из item_delta, распознавание ошибок и exit_code
        raise NotImplementedError("parse_stream не реализован")
