#!/usr/bin/env python3
r"""Тестовый раннер для упражнения agents-rules.
Проверяет функцию validate_agents_content(content: str) -> tuple[bool, str],
которая валидирует структуру AGENTS.md:
- Требует наличие обязательных секций (# или ##)
- Запрещает хранение секретов и токенов (sk-..., ghp_..., password:)
- Запрещает хардкод локальных путей компьютера (C:\Users\, /home/)
"""

import sys


def run_tests() -> int:
    try:
        from validator import validate_agents_content
    except ImportError as e:
        print(f"FAIL: Не удалось импортировать validator.validate_agents_content: {e}", file=sys.stderr)
        return 1

    # 1. Корректный AGENTS.md
    valid_doc = """# Руководство проекта
## Команды сборки и тестов
- `python scripts/verify.py`
## Правила оформления
- Использовать относительные пути
- Соблюдать стандарты кодирования
"""
    ok, err = validate_agents_content(valid_doc)
    if not ok:
        print(f"FAIL: Ожидался PASS для корректного документа, получено: {err}", file=sys.stderr)
        return 1

    # 2. Ошибка: секрет (API-ключ)
    secret_doc = valid_doc + "\nOPENAI_KEY = sk-proj-1234567890abcdef1234\n"
    ok, err = validate_agents_content(secret_doc)
    if ok:
        print("FAIL: Документ с API-ключом sk-... ошибочно прошел валидацию!", file=sys.stderr)
        return 1

    # 3. Ошибка: абсолютный системный путь компьютера
    path_doc = valid_doc + "\nРабочая папка разработчика: C:\\Users\\Developer\\project\n"
    ok, err = validate_agents_content(path_doc)
    if ok:
        print("FAIL: Документ с абсолютным путем пользователя C:\\Users ошибочно прошел валидацию!", file=sys.stderr)
        return 1

    # 4. Ошибка: отсутствие обязательных секций
    empty_doc = "# Пустой заголовок\nБез описания правил и команд."
    ok, err = validate_agents_content(empty_doc)
    if ok:
        print("FAIL: Документ без обязательных секций ошибочно прошел валидацию!", file=sys.stderr)
        return 1

    print("PASS: Все тесты валидатора AGENTS.md успешно пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
