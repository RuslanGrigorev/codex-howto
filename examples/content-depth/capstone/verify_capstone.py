#!/usr/bin/env python3
"""Скрипт сквозной проверки итогового проекта C01: политика diff, тесты и артефакты (ADR-CD-04, Finding 8)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# UTF-8 reconfigure
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def check_diff_policy(original_test: Path, student_test: Path) -> list[str]:
    """Политика diff: независимые тесты НЕ ДОЛЖНЫ модифицироваться студентом."""
    errors = []
    if not student_test.is_file():
        errors.append("Файл тестов test_metrics.py не найден в рабочем каталоге")
        return errors

    orig_hash = compute_sha256(original_test)
    student_hash = compute_sha256(student_test)
    if orig_hash != student_hash:
        errors.append(
            "Нарушение политики diff: файл независимых тестов test_metrics.py был изменён! "
            "Ослабление проверок запрещено контрактом курса."
        )
    return errors


def run_independent_tests(workspace: Path) -> tuple[bool, str]:
    test_file = workspace / "test_metrics.py"
    if not test_file.is_file():
        return False, "test_metrics.py не найден"

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-S", str(test_file)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env
    )
    output = proc.stdout + "\n" + proc.stderr
    return proc.returncode == 0, output


def verify_capstone(workspace: Path, starter_dir: Path) -> dict:
    results = {
        "status": "PASS",
        "diff_policy": "PASS",
        "tests_passed": False,
        "errors": []
    }

    # 1. Проверка политики diff
    diff_errs = check_diff_policy(starter_dir / "test_metrics.py", workspace / "test_metrics.py")
    if diff_errs:
        results["diff_policy"] = "FAIL"
        results["errors"].extend(diff_errs)
        results["status"] = "FAIL"
        return results

    # 2. Запуск независимых проверок
    passed, test_output = run_independent_tests(workspace)
    results["tests_passed"] = passed
    if not passed:
        results["status"] = "FAIL"
        results["errors"].append("Независимые тесты test_metrics.py завершились с ошибкой:\n" + test_output[-500:])
    else:
        results["message"] = "Все независимые тесты успешно пройдены."

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    starter = root / "starter"
    solution = root / "solution"

    ws = args.workspace or solution
    # Копируем test_metrics.py в ws, если его там нет (для solution)
    if not (ws / "test_metrics.py").is_file():
        import shutil
        shutil.copy2(starter / "test_metrics.py", ws / "test_metrics.py")

    res = verify_capstone(ws, starter)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
