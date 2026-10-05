#!/usr/bin/env python3
"""Хук Stop: проверка готовности задачи, успешности тестов и защита от рекурсии."""
from __future__ import annotations
import json
import sys

# Обеспечиваем UTF-8
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
                "reason": "Пустой ввод в хук Stop: требуется JSON полезной нагрузки."
            }, ensure_ascii=False) + "\n")
            return
        payload = json.loads(raw_input)
    except Exception as exc:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": f"Ошибка парсинга JSON в хуке Stop: {exc}"
        }, ensure_ascii=False) + "\n")
        return

    # Защита от бесконечной рекурсии (H04 recursion guard)
    if payload.get("stop_hook_active") is True or payload.get("recursion_depth", 0) > 1:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": "Завершение отклонено: обнаружена рекурсивная активация хука Stop (stop_hook_active = true). Защита от зацикливания."
        }, ensure_ascii=False) + "\n")
        return

    tests_passed = payload.get("tests_passed")
    if tests_passed is not True:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": "Завершение отклонено: обязательные верификационные тесты не пройдены (tests_passed != true).",
            "stop_hook_active": True
        }, ensure_ascii=False) + "\n")
        return

    sys.stdout.write(json.dumps({
        "status": "allow",
        "message": "Верификация завершения успешна: тесты пройдены."
    }, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
