#!/usr/bin/env python3
"""Тестовый раннер для упражнения safety-guard.
Проверяет функцию validate_target_path(path_str, workspace_root),
которая должна разрешать только пути строго внутри workspace_root,
блокируя выход за пределы каталога (path traversal, абсолютные пути вне workspace).
"""

import sys
from pathlib import Path


def run_tests() -> int:
    try:
        from guard import validate_target_path
    except ImportError as e:
        print(f"FAIL: Не удалось импортировать guard.validate_target_path: {e}", file=sys.stderr)
        return 1

    workspace = Path("/tmp/mock_workspace").resolve()

    # 1. Корректные пути внутри workspace
    valid_cases = [
        "file.txt",
        "subdir/nested.py",
        "./deep/path/data.json",
    ]
    for rel in valid_cases:
        res = validate_target_path(rel, workspace)
        if not res or not str(res).startswith(str(workspace)):
            print(f"FAIL: Ожидался допуск для пути внутри workspace: '{rel}', получено: {res}", file=sys.stderr)
            return 1

    # 2. Недопустимые попытки выхода за пределы workspace (path traversal)
    dangerous_cases = [
        "../outside.txt",
        "subdir/../../escape.txt",
        "/etc/passwd",
        "~/.codex/config.toml",
        "C:\\Windows\\System32",
    ]
    for bad in dangerous_cases:
        try:
            res = validate_target_path(bad, workspace)
            if res is not None:
                print(f"FAIL: Опасный путь '{bad}' не был отклонен! Получено: {res}", file=sys.stderr)
                return 1
        except (ValueError, PermissionError):
            # Исключение также считается корректным отклонением опасного пути
            pass

    print("PASS: Все проверки безопасности и изоляции путей пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
