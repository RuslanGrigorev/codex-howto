#!/usr/bin/env python3
"""Хук UserPromptSubmit: фильтрация случайных секретов в промпте."""
import json
import re
import sys

def main():
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception:
        sys.stdout.write(json.dumps({"status": "allow"}) + "\n")
        return

    prompt = payload.get("prompt", "")
    # Проверка на типичные паттерны API ключей
    if re.search(r"sk-[a-zA-Z0-9]{32,}", prompt) or "BEGIN OPENSSH PRIVATE KEY" in prompt:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": "В промпте обнаружен приватный ключ или секретный токен! Запрос заблокирован."
        }) + "\n")
        return

    sys.stdout.write(json.dumps({"status": "allow"}) + "\n")

if __name__ == "__main__":
    main()
