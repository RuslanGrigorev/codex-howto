#!/usr/bin/env python3
"""Парсинг и валидация потока JSONL от codex exec."""
import json
from pathlib import Path

def main():
    sample_file = Path(__file__).parent / "sample_output.jsonl"
    events = [json.loads(line) for line in sample_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    
    assert any(e.get("event") == "tool_call" for e in events), "Нет событий вызова инструмента"
    assert any(e.get("event") == "turn_complete" for e in events), "Нет события завершения"
    print(f"Успешно обработано {len(events)} событий автоматизации")
    print("PASS: A01 batch exec jsonl stream parsed")

if __name__ == "__main__":
    main()
