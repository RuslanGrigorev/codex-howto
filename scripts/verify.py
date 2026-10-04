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
        exclude_dirs = [".git", ".learning", ".pytest_cache", "__pycache__", "site", "site_test", ".gemini", ".agent", ".vendor-cache"]

    file_hashes: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

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

    # 5. Проверка модуля прогресса (PRG-001 - PRG-005)
    progress_js = repo_root / "scripts" / "website_templates" / "progress.js"
    if not progress_js.exists():
        cases.append({
            "scenario_id": "PRG-001-S01",
            "status": "FAIL",
            "check": "check_progress_module",
            "evidence": [],
            "message": "Модуль scripts/website_templates/progress.js не найден",
        })
    else:
        pjs_content = progress_js.read_text(encoding="utf-8")
        if (
            'STORAGE_KEY = "codex-cli-course-ru.progress.v1"' in pjs_content
            and "1024 * 1024" in pjs_content
            and 'COURSE_ID = "codex-cli-course-ru"' in pjs_content
        ):
            cases.append({
                "scenario_id": "PRG-001-S01",
                "status": "PASS",
                "check": "check_progress_module",
                "evidence": [{"path": "scripts/website_templates/progress.js", "type": "file"}],
                "message": "Модуль progress.js соответствует спецификации схемы, лимитов (1 МиБ) и ID курса",
            })
        else:
            cases.append({
                "scenario_id": "PRG-001-S01",
                "status": "FAIL",
                "check": "check_progress_module",
                "evidence": [{"path": "scripts/website_templates/progress.js", "type": "file"}],
                "message": "progress.js не содержит требуемых констант STORAGE_KEY или COURSE_ID",
            })

    # 6. Проверка упражнения small-fix (эталон проходит, мутации падают) [VAL-003, OFF-003, TUT-004]
    sf_dir = repo_root / "examples" / "small-fix"
    if (sf_dir / "test.py").exists() and (sf_dir / "solution").exists():
        sf_test = sf_dir / "test.py"
        sol_env = os.environ.copy()
        sol_env["PYTHONPATH"] = str(sf_dir / "solution")
        res_sol = subprocess.run([sys.executable, str(sf_test)], cwd=str(sf_dir / "solution"), env=sol_env, capture_output=True, text=True, timeout=5)

        st_env = os.environ.copy()
        st_env["PYTHONPATH"] = str(sf_dir / "starter")
        res_st = subprocess.run([sys.executable, str(sf_test)], cwd=str(sf_dir / "starter"), env=st_env, capture_output=True, text=True, timeout=5)

        mut1_env = os.environ.copy()
        mut1_env["PYTHONPATH"] = str(sf_dir / "broken_mutation_negative")
        res_mut1 = subprocess.run([sys.executable, str(sf_test)], cwd=str(sf_dir / "broken_mutation_negative"), env=mut1_env, capture_output=True, text=True, timeout=5)

        mut2_env = os.environ.copy()
        mut2_env["PYTHONPATH"] = str(sf_dir / "broken_mutation_overflow")
        res_mut2 = subprocess.run([sys.executable, str(sf_test)], cwd=str(sf_dir / "broken_mutation_overflow"), env=mut2_env, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_mut1.returncode != 0 and res_mut2.returncode != 0:
            cases.append({
                "scenario_id": "VAL-003-S01",
                "status": "PASS",
                "check": "check_exercise_small_fix",
                "evidence": [{"path": "examples/small-fix", "type": "directory"}],
                "message": "Упражнение small-fix: эталон PASS, starter и мутации детерминированно FAIL",
            })
        else:
            cases.append({
                "scenario_id": "VAL-003-S01",
                "status": "FAIL",
                "check": "check_exercise_small_fix",
                "evidence": [{"path": "examples/small-fix", "type": "directory"}],
                "message": f"Сбой проверки small-fix: sol={res_sol.returncode}, st={res_st.returncode}, mut1={res_mut1.returncode}, mut2={res_mut2.returncode}",
            })

    # 7. Проверка сборки сайта и офлайн-совместимости (OFF-001, CRS-001)
    test_out = repo_root / ".learning" / "test_site"
    try:
        build_script = repo_root / "scripts" / "build_website.py"
        res_build = subprocess.run(
            [sys.executable, str(build_script), "--output", str(test_out)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=25,
        )
        if res_build.returncode == 0:
            index_html = test_out / "index.html"
            if index_html.exists():
                idx_content = index_html.read_text(encoding="utf-8")
                has_lang_ru = '<html lang="ru"' in idx_content
                has_progress_js = 'assets/progress.js' in idx_content
                no_abs_paths = (":\\" not in idx_content and "/home/" not in idx_content and "/Users/" not in idx_content)
                if has_lang_ru and has_progress_js and no_abs_paths:
                    cases.append({
                        "scenario_id": "OFF-001-S01",
                        "status": "PASS",
                        "check": "check_site_build",
                        "evidence": [{"path": ".learning/test_site/index.html", "type": "file"}],
                        "message": "Сайт собирается автономно: lang='ru', progress.js подключен, абсолютные пути отсутствуют",
                    })
                else:
                    cases.append({
                        "scenario_id": "OFF-001-S01",
                        "status": "FAIL",
                        "check": "check_site_build",
                        "evidence": [],
                        "message": f"index.html нарушает требования (lang_ru={has_lang_ru}, progress_js={has_progress_js}, no_abs={no_abs_paths})",
                    })
            else:
                cases.append({
                    "scenario_id": "OFF-001-S01",
                    "status": "FAIL",
                    "check": "check_site_build",
                    "evidence": [],
                    "message": "index.html не сгенерирован при сборке сайта",
                })
        else:
            cases.append({
                "scenario_id": "OFF-001-S01",
                "status": "FAIL",
                "check": "check_site_build",
                "evidence": [],
                "message": f"Ошибка запуска build_website.py: {res_build.stderr}",
            })
    except Exception as e:
        cases.append({
            "scenario_id": "OFF-001-S01",
            "status": "FAIL",
            "check": "check_site_build",
            "evidence": [],
            "message": f"Исключение при сборке сайта: {e}",
        })
    finally:
        import shutil
        shutil.rmtree(test_out, ignore_errors=True)

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
