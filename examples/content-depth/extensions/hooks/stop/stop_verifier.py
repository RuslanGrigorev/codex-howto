#!/usr/bin/env python3
"""Хук Stop: проверка готовности задачи и успешности тестов перед завершением."""
import json
import sys

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.stdout.write(json.dumps({
                "status": "deny",
                "reason": "Пустой ввод в хук Stop: требуется JSON полезной нагрузки."
            }) + "\n")
            return
        payload = json.loads(raw_input)
    except Exception as exc:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": f"Ошибка парсинга JSON в хуке Stop: {exc}"
        }) + "\n")
        return

    tests_passed = payload.get("tests_passed")
    if tests_passed is not True:
        sys.stdout.write(json.dumps({
            "status": "deny",
            "reason": "Завершение отклонено: обязательные верификационные тесты не пройдены (tests_passed != true)."
        }) + "\n")
        return

    sys.stdout.write(json.dumps({
        "status": "allow",
        "message": "Верификация завершения успешна: тесты пройдены."
    }) + "\n")

if __name__ == "__main__":
    main()
