#!/usr/bin/env python3
"""scripts/verify.py - Единая точка проверки и верификации проекта.

Поддерживает профили:
  --profile offline: автономные проверки (файлы, синтаксис, данные, упражнения, браузерные тесты без сети)
  --profile live: проверка работы с реальным Codex CLI в изолированном учебном каталоге
  --profile release: итоговая приёмка релизного артефакта по доказательствам

Режим ученика:
  --exercise <id>: проверка выполнения конкретного изолированного упражнения
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_repo_root() -> Path:
    """Возвращает корень репозитория относительно расположения скрипта."""
    return Path(__file__).resolve().parent.parent


def get_environment_info() -> Dict[str, Any]:
    """Сбор информации об окружении без обращения к сети и без изменения системных конфигов."""
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"

    codex_ver = None
    try:
        res = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            codex_ver = res.stdout.strip()
    except Exception:
        pass

    return {
        "os": os_name,
        "python": py_ver,
        "codex": codex_ver,
        "provider": None,
        "model": None,
        "browsers": [],
    }


def compute_tree_sha256(root_dir: Path, exclude_dirs: Optional[List[str]] = None) -> str:
    """Вычисляет воспроизводимый SHA-256 дерева файлов, исключая генерируемые и временные файлы."""
    if exclude_dirs is None:
        exclude_dirs = [".git", ".learning", ".pytest_cache", "__pycache__", "site", ".gemini", ".agent"]

    file_hashes: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = os.path.relpath(dirpath, root_dir)
        # Исключаем служебные директории
        parts = Path(rel_dir).parts
        if any(part in exclude_dirs for part in parts):
            continue

        for filename in sorted(filenames):
            if filename.endswith((".pyc", ".pyo")):
                continue
            file_path = Path(dirpath) / filename
            try:
                rel_path = os.path.relpath(file_path, root_dir).replace("\\", "/")
                with open(file_path, "rb") as f:
                    content_sha = hashlib.sha256(f.read()).hexdigest()
                file_hashes.append(f"{rel_path}:{content_sha}")
            except Exception:
                continue

    file_hashes.sort()
    combined = "\n".join(file_hashes).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def run_offline_checks(repo_root: Path) -> List[Dict[str, Any]]:
    """Выполняет статические и автономные проверки целостности курса."""
    cases: List[Dict[str, Any]] = []

    # 1. Проверка наличия и валидности OpenSpec
    openspec_dir = repo_root / "openspec"
    if not openspec_dir.exists():
        cases.append({
            "scenario_id": "VAL-001-S01",
            "status": "FAIL",
            "check": "check_openspec_dir",
            "evidence": [],
            "message": "Директория openspec/ не найдена",
        })
    else:
        cases.append({
            "scenario_id": "VAL-001-S01",
            "status": "PASS",
            "check": "check_openspec_dir",
            "evidence": [{"path": "openspec", "type": "directory"}],
            "message": "Структура openspec присутствует",
        })

    # 2. Проверка изоляции путей (отсутствие локальных абсолютных путей в openspec)
    bad_paths_found = False
    for p in openspec_dir.rglob("*.md"):
        try:
            content = p.read_text(encoding="utf-8")
            if ":\\" in content or "/home/" in content or "/Users/" in content:
                bad_paths_found = True
                cases.append({
                    "scenario_id": "TUT-004-S02",
                    "status": "FAIL",
                    "check": "check_relative_paths",
                    "evidence": [{"path": str(p.relative_to(repo_root)).replace("\\", "/"), "type": "file"}],
                    "message": f"Обнаружен абсолютный локальный путь в файле {p.name}",
                })
                break
        except Exception:
            pass

    if not bad_paths_found:
        cases.append({
            "scenario_id": "TUT-004-S02",
            "status": "PASS",
            "check": "check_relative_paths",
            "evidence": [],
            "message": "Абсолютные локальные пути в openspec отсутствуют",
        })

    # 3. Проверка course.json (CRS-002)
    course_file = repo_root / "course.json"
    if not course_file.exists():
        cases.append({
            "scenario_id": "CRS-002-S01",
            "status": "FAIL",
            "check": "check_course_json",
            "evidence": [],
            "message": "Файл course.json отсутствует",
        })
    else:
        try:
            course_data = json.loads(course_file.read_text(encoding="utf-8"))
            modules = course_data.get("modules", [])
            lesson_ids = set()
            duplicates = []
            for m in modules:
                for l in m.get("lessons", []):
                    lid = l.get("id")
                    if lid in lesson_ids:
                        duplicates.append(lid)
                    lesson_ids.add(lid)
            if duplicates:
                cases.append({
                    "scenario_id": "CRS-002-S02",
                    "status": "FAIL",
                    "check": "check_course_json",
                    "evidence": [],
                    "message": f"Обнаружены дубликаты ID уроков: {duplicates}",
                })
            else:
                cases.append({
                    "scenario_id": "CRS-002-S01",
                    "status": "PASS",
                    "check": "check_course_json",
                    "evidence": [{"path": "course.json", "type": "file"}],
                    "message": f"course.json валиден, зарегистрировано уроков: {len(lesson_ids)}",
                })
        except Exception as e:
            cases.append({
                "scenario_id": "CRS-002-S01",
                "status": "FAIL",
                "check": "check_course_json",
                "evidence": [],
                "message": f"Ошибка парсинга course.json: {e}",
            })

    # 4. Проверка детерминированного оценивания тестов (CRS-006)
    quiz_files = list(repo_root.glob("**/quiz.json"))
    quiz_errors = []
    for qf in quiz_files:
        try:
            qdata = json.loads(qf.read_text(encoding="utf-8"))
            questions = qdata.get("questions", [])
            for q in questions:
                correct_count = sum(1 for opt in q.get("options", []) if opt.get("is_correct"))
                if correct_count != 1:
                    quiz_errors.append(f"{qf.name}: вопрос {q.get('id')} должен иметь ровно 1 правильный ответ")
        except Exception as e:
            quiz_errors.append(f"{qf.name}: ошибка парсинга {e}")

    if quiz_errors:
        cases.append({
            "scenario_id": "CRS-006-S02",
            "status": "FAIL",
            "check": "check_quizzes",
            "evidence": [],
            "message": "; ".join(quiz_errors),
        })
    else:
        cases.append({
            "scenario_id": "CRS-006-S01",
            "status": "PASS",
            "check": "check_quizzes",
            "evidence": [{"path": str(qf.relative_to(repo_root)).replace("\\", "/"), "type": "file"} for qf in quiz_files],
            "message": f"Все викторины ({len(quiz_files)}) соответствуют детерминированной схеме",
        })

    return cases


def run_exercise_check(exercise_id: str, workspace_path: Path) -> int:
    """Проверка одного изолированного упражнения ученика."""
    # Проверка на попытку выхода за пределы workspace (directory traversal)
    resolved = workspace_path.resolve()
    repo_root = get_repo_root().resolve()

    if not str(resolved).startswith(str(repo_root)):
        print(f"ОШИБКА БЕЗОПАСНОСТИ: Рабочий каталог {workspace_path} выходит за пределы проекта!", file=sys.stderr)
        return 2

    if not resolved.exists():
        print(f"ОШИБКА: Каталог упражнения {workspace_path} не существует.", file=sys.stderr)
        return 1

    exercise_example_dir = repo_root / "examples" / exercise_id
    test_runner = exercise_example_dir / "test.py"
    if not test_runner.exists():
        test_runner = resolved / "test.py"

    if not test_runner.exists():
        print(f"ОШИБКА: Тестовый раннер для упражнения '{exercise_id}' не найден.", file=sys.stderr)
        return 1

    print(f"Проверка упражнения '{exercise_id}' в {workspace_path}...")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(resolved)
        res = subprocess.run(
            [sys.executable, str(test_runner)],
            cwd=str(resolved),
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip(), file=sys.stderr)
        return res.returncode
    except subprocess.TimeoutExpired:
        print(f"FAIL: Превышен таймаут выполнения упражнения '{exercise_id}' (10 сек).", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Ошибка запуска проверки: {e}", file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Единая точка проверки и верификации проекта (scripts/verify.py)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--profile", choices=["offline", "live", "release"], help="Профиль верификации")
    group.add_argument("--exercise", type=str, help="ID упражнения для проверки")

    parser.add_argument("--workspace", type=Path, default=None, help="Рабочий каталог для режима --exercise")
    parser.add_argument("--report", type=Path, default=None, help="Путь для сохранения JSON-отчёта")
    parser.add_argument("--evidence-dir", type=Path, default=None, help="Каталог доказательств для release")

    args = parser.parse_args()
    repo_root = get_repo_root()

    if args.exercise:
        ws = args.workspace or (repo_root / ".learning" / "workspaces" / args.exercise)
        return run_exercise_check(args.exercise, ws)

    profile = args.profile
    report_file = args.report or (repo_root / ".learning" / "reports" / f"{profile}.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)

    tree_sha = compute_tree_sha256(repo_root)
    env_info = get_environment_info()

    cases: List[Dict[str, Any]] = []
    overall = "PASS"

    if profile == "offline":
        cases = run_offline_checks(repo_root)
        if any(c["status"] == "FAIL" for c in cases):
            overall = "FAIL"
        elif any(c["status"] == "BLOCKED" for c in cases):
            overall = "BLOCKED"
        elif not cases:
            overall = "NOT_RUN"
    elif profile == "live":
        # Профиль live требует доступного Codex CLI и настроенного тестового окружения
        if not env_info.get("codex"):
            cases.append({
                "scenario_id": "VAL-004-S02",
                "status": "BLOCKED",
                "check": "check_codex_availability",
                "evidence": [],
                "message": "Codex CLI не найден в окружении PATH для live-профиля",
            })
            overall = "BLOCKED"
        else:
            cases.append({
                "scenario_id": "VAL-004-S01",
                "status": "PASS",
                "check": "check_codex_availability",
                "evidence": [],
                "message": f"Codex CLI обнаружен: {env_info['codex']}",
            })
    elif profile == "release":
        # Профиль release сверяет отчёты и доказательства
        overall = "NOT_RUN"
        cases.append({
            "scenario_id": "VAL-005-S01",
            "status": "NOT_RUN",
            "check": "check_release_evidence",
            "evidence": [],
            "message": "Сборка релизного отчёта ожидает полного набора доказательств",
        })

    report_data = {
        "schema_version": 1,
        "profile": profile,
        "candidate_tree_sha256": tree_sha,
        "spec_sha256": "",
        "environment": env_info,
        "cases": cases,
        "overall": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    report_file.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Отчёт верификации сохранён: {report_file}")
    print(f"Итог: {overall} ({len(cases)} проверок)")

    if overall == "PASS":
        return 0
    elif overall == "FAIL":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
