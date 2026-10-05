#!/usr/bin/env python3
"""Хук PostToolUse: аудит выполненных действий."""
import json
import sys
from pathlib import Path

def main():
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception:
        sys.stdout.write(json.dumps({"status": "ok"}) + "\n")
        return

    tool = payload.get("tool_name", "unknown")
    # Логируем действие в stderr или в файл
    sys.stderr.write(f"[AUDIT] Инструмент {tool} успешно завершил исполнение.\n")
    sys.stdout.write(json.dumps({"status": "ok"}) + "\n")

if __name__ == "__main__":
    main()
