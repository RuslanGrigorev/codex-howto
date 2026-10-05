#!/usr/bin/env python3
"""Хук плагина UserPromptSubmit: фильтрация секретов с fail-closed семантикой."""
from __future__ import annotations
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.stdout.write(json.dumps({
                "status": "deny",
                "reason": "Пустой ввод в хук плагина UserPromptSubmit: требуется JSON полезной нагрузки."
            }, ensure_ascii=False) + "\n")
            return
        payload = json.loads(raw_input)
    except Exception as exc:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": f"Ошибка парсинга JSON в хуке плагина: {exc}"
        }, ensure_ascii=False) + "\n")
        return

    prompt = payload.get("prompt", "")
    if re.search(r"sk-[a-zA-Z0-9]{32,}", prompt) or "BEGIN OPENSSH PRIVATE KEY" in prompt or "BEGIN RSA PRIVATE KEY" in prompt:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": "В промпте обнаружен приватный ключ или секретный токен! Запрос заблокирован плагином."
        }, ensure_ascii=False) + "\n")
        return

    sys.stdout.write(json.dumps({
        "status": "allow",
        "message": "Промпт проверен плагином: секреты не обнаружены."
    }, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
