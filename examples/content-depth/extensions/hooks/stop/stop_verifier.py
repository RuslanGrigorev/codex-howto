#!/usr/bin/env python3
"""Хук Stop: проверка готовности задачи перед завершением."""
import json
import sys

def main():
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception:
        sys.stdout.write(json.dumps({"status": "allow"}) + "\n")
        return

    # В учебном примере проверяем готовность
    sys.stdout.write(json.dumps({"status": "allow"}) + "\n")

if __name__ == "__main__":
    main()
