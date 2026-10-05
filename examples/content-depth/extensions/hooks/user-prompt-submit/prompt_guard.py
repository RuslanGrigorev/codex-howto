#!/usr/bin/env python3
"""Хук UserPromptSubmit: фильтрация случайных секретов в промпте с fail-closed семантикой."""
import json
import re
import sys

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.stdout.write(json.dumps({
                "status": "deny",
                "reason": "Пустой ввод в хук UserPromptSubmit: требуется JSON полезной нагрузки."
            }) + "\n")
            return
        payload = json.loads(raw_input)
    except Exception as exc:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": f"Ошибка парсинга JSON в хуке UserPromptSubmit: {exc}"
        }) + "\n")
        return

    prompt = payload.get("prompt", "")
    if re.search(r"sk-[a-zA-Z0-9]{32,}", prompt) or "BEGIN OPENSSH PRIVATE KEY" in prompt or "BEGIN RSA PRIVATE KEY" in prompt:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": "В промпте обнаружен приватный ключ или секретный токен! Запрос заблокирован."
        }) + "\n")
        return

    sys.stdout.write(json.dumps({"status": "allow"}) + "\n")

if __name__ == "__main__":
    main()
