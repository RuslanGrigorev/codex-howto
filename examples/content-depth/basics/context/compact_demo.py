#!/usr/bin/env python3
"""Демонстрация анализа и сжатия контекста сессии."""
import json
from pathlib import Path

def main():
    log_file = Path(__file__).parent / "session_sample.jsonl"
    events = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    
    total_turns = max(e.get("turn", 0) for e in events)
    compaction_events = [e for e in events if e.get("type") == "compaction"]
    
    print(f"Загружено событий: {len(events)}, ходов: {total_turns}")
    print(f"Событий сжатия: {len(compaction_events)}")
    if compaction_events:
        print(f"Сводка после сжатия: {compaction_events[0].get('summary')}")
    print("PASS: B03 context demo")

if __name__ == "__main__":
    main()
