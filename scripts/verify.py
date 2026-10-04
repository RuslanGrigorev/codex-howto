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
import zipfile


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

    # 7. Проверка упражнения safety-guard (CRS-004, TUT-004)
    sg_dir = repo_root / "examples" / "safety-guard"
    if (sg_dir / "test.py").exists() and (sg_dir / "solution").exists():
        sg_test = str((sg_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, sg_test], cwd=str(sg_dir / "solution"), env={"PYTHONPATH": str(sg_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, sg_test], cwd=str(sg_dir / "starter"), env={"PYTHONPATH": str(sg_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, sg_test], cwd=str(sg_dir / "broken_mutation_relative"), env={"PYTHONPATH": str(sg_dir / "broken_mutation_relative")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, sg_test], cwd=str(sg_dir / "broken_mutation_allow_all"), env={"PYTHONPATH": str(sg_dir / "broken_mutation_allow_all")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "TUT-004-S01",
                "status": "PASS",
                "check": "check_exercise_safety_guard",
                "evidence": [{"path": "examples/safety-guard", "type": "directory"}],
                "message": "Упражнение safety-guard: изоляция путей и защита от обхода каталога доказана",
            })
        else:
            cases.append({
                "scenario_id": "TUT-004-S01",
                "status": "FAIL",
                "check": "check_exercise_safety_guard",
                "evidence": [{"path": "examples/safety-guard", "type": "directory"}],
                "message": f"Сбой проверки safety-guard: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 8. Проверка упражнения agents-rules (CRS-004)
    ar_dir = repo_root / "examples" / "agents-rules"
    if (ar_dir / "test.py").exists() and (ar_dir / "solution").exists():
        ar_test = str((ar_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, ar_test], cwd=str(ar_dir / "solution"), env={"PYTHONPATH": str(ar_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, ar_test], cwd=str(ar_dir / "starter"), env={"PYTHONPATH": str(ar_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, ar_test], cwd=str(ar_dir / "broken_mutation_secrets"), env={"PYTHONPATH": str(ar_dir / "broken_mutation_secrets")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, ar_test], cwd=str(ar_dir / "broken_mutation_paths"), env={"PYTHONPATH": str(ar_dir / "broken_mutation_paths")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "CRS-004-S01",
                "status": "PASS",
                "check": "check_exercise_agents_rules",
                "evidence": [{"path": "examples/agents-rules", "type": "directory"}],
                "message": "Упражнение agents-rules: валидация AGENTS.md, блокировка секретов и путей доказана",
            })
        else:
            cases.append({
                "scenario_id": "CRS-004-S01",
                "status": "FAIL",
                "check": "check_exercise_agents_rules",
                "evidence": [{"path": "examples/agents-rules", "type": "directory"}],
                "message": f"Сбой проверки agents-rules: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 9. Проверка упражнения session-restore (CRS-004-S02)
    sr_dir = repo_root / "examples" / "session-restore"
    if (sr_dir / "test.py").exists() and (sr_dir / "solution").exists():
        sr_test = str((sr_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, sr_test], cwd=str(sr_dir / "solution"), env={"PYTHONPATH": str(sr_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, sr_test], cwd=str(sr_dir / "starter"), env={"PYTHONPATH": str(sr_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, sr_test], cwd=str(sr_dir / "broken_mutation_mix_git"), env={"PYTHONPATH": str(sr_dir / "broken_mutation_mix_git")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, sr_test], cwd=str(sr_dir / "broken_mutation_lost_history"), env={"PYTHONPATH": str(sr_dir / "broken_mutation_lost_history")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "CRS-004-S02",
                "status": "PASS",
                "check": "check_exercise_session_restore",
                "evidence": [{"path": "examples/session-restore", "type": "directory"}],
                "message": "Упражнение session-restore: изоляция сессии от Git-состояния файлов доказана",
            })
        else:
            cases.append({
                "scenario_id": "CRS-004-S02",
                "status": "FAIL",
                "check": "check_exercise_session_restore",
                "evidence": [{"path": "examples/session-restore", "type": "directory"}],
                "message": f"Сбой проверки session-restore: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 10. Проверка упражнения custom-skill (CRS-005-S01)
    cs_dir = repo_root / "examples" / "custom-skill"
    if (cs_dir / "test.py").exists() and (cs_dir / "solution").exists():
        cs_test = str((cs_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, cs_test], cwd=str(cs_dir / "solution"), env={"PYTHONPATH": str(cs_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, cs_test], cwd=str(cs_dir / "starter"), env={"PYTHONPATH": str(cs_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, cs_test], cwd=str(cs_dir / "broken_mutation_no_frontmatter"), env={"PYTHONPATH": str(cs_dir / "broken_mutation_no_frontmatter")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, cs_test], cwd=str(cs_dir / "broken_mutation_leak_paths"), env={"PYTHONPATH": str(cs_dir / "broken_mutation_leak_paths")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "CRS-005-S01",
                "status": "PASS",
                "check": "check_exercise_custom_skill",
                "evidence": [{"path": "examples/custom-skill", "type": "directory"}],
                "message": "Упражнение custom-skill: валидация frontmatter и блокировка путей доказана",
            })
        else:
            cases.append({
                "scenario_id": "CRS-005-S01",
                "status": "FAIL",
                "check": "check_exercise_custom_skill",
                "evidence": [{"path": "examples/custom-skill", "type": "directory"}],
                "message": f"Сбой проверки custom-skill: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 11. Проверка локального справочника (CRS-005-S02)
    ref_dir = repo_root / "reference"
    ref_files = ["commands.md", "config.md", "skills.md"]
    missing_refs = [rf for rf in ref_files if not (ref_dir / rf).exists()]
    if missing_refs:
        cases.append({
            "scenario_id": "CRS-005-S02",
            "status": "FAIL",
            "check": "check_local_reference",
            "evidence": [],
            "message": f"В справочнике reference/ отсутствуют файлы: {missing_refs}",
        })
    else:
        cases.append({
            "scenario_id": "CRS-005-S02",
            "status": "PASS",
            "check": "check_local_reference",
            "evidence": [{"path": f"reference/{rf}", "type": "file"} for rf in ref_files],
            "message": "Локальный офлайн-справочник reference/ укомплектован (commands, config, skills)",
        })

    # 12. Проверка упражнения local-mcp (CRS-003, OFF-002)
    mcp_dir = repo_root / "examples" / "local-mcp"
    if (mcp_dir / "test.py").exists() and (mcp_dir / "solution").exists():
        mcp_test = str((mcp_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, mcp_test], cwd=str(mcp_dir / "solution"), env={"PYTHONPATH": str(mcp_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, mcp_test], cwd=str(mcp_dir / "starter"), env={"PYTHONPATH": str(mcp_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, mcp_test], cwd=str(mcp_dir / "broken_mutation_no_bounds"), env={"PYTHONPATH": str(mcp_dir / "broken_mutation_no_bounds")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, mcp_test], cwd=str(mcp_dir / "broken_mutation_bad_rpc"), env={"PYTHONPATH": str(mcp_dir / "broken_mutation_bad_rpc")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "CRS-003-S01",
                "status": "PASS",
                "check": "check_exercise_local_mcp",
                "evidence": [{"path": "examples/local-mcp", "type": "directory"}],
                "message": "Упражнение local-mcp: безопасный stdio MCP сервер и блокировка Directory Traversal доказаны",
            })
        else:
            cases.append({
                "scenario_id": "CRS-003-S01",
                "status": "FAIL",
                "check": "check_exercise_local_mcp",
                "evidence": [{"path": "examples/local-mcp", "type": "directory"}],
                "message": f"Сбой проверки local-mcp: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 13. Проверка упражнения cli-stream (CRS-004-S03)
    cs_stream_dir = repo_root / "examples" / "cli-stream"
    if (cs_stream_dir / "test.py").exists() and (cs_stream_dir / "solution").exists():
        cs_stream_test = str((cs_stream_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, cs_stream_test], cwd=str(cs_stream_dir / "solution"), env={"PYTHONPATH": str(cs_stream_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, cs_stream_test], cwd=str(cs_stream_dir / "starter"), env={"PYTHONPATH": str(cs_stream_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, cs_stream_test], cwd=str(cs_stream_dir / "broken_mutation_single_json"), env={"PYTHONPATH": str(cs_stream_dir / "broken_mutation_single_json")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, cs_stream_test], cwd=str(cs_stream_dir / "broken_mutation_ignore_errors"), env={"PYTHONPATH": str(cs_stream_dir / "broken_mutation_ignore_errors")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "CRS-004-S03",
                "status": "PASS",
                "check": "check_exercise_cli_stream",
                "evidence": [{"path": "examples/cli-stream", "type": "directory"}],
                "message": "Упражнение cli-stream: потоковый парсинг JSONL и выявление ошибок доказаны",
            })
        else:
            cases.append({
                "scenario_id": "CRS-004-S03",
                "status": "FAIL",
                "check": "check_exercise_cli_stream",
                "evidence": [{"path": "examples/cli-stream", "type": "directory"}],
                "message": f"Сбой проверки cli-stream: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 14. Проверка упражнения extension-hook (TUT-004-S03)
    eh_dir = repo_root / "examples" / "extension-hook"
    if (eh_dir / "test.py").exists() and (eh_dir / "solution").exists():
        eh_test = str((eh_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, eh_test], cwd=str(eh_dir / "solution"), env={"PYTHONPATH": str(eh_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, eh_test], cwd=str(eh_dir / "starter"), env={"PYTHONPATH": str(eh_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, eh_test], cwd=str(eh_dir / "broken_mutation_allow_insecure"), env={"PYTHONPATH": str(eh_dir / "broken_mutation_allow_insecure")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, eh_test], cwd=str(eh_dir / "broken_mutation_silent_fail"), env={"PYTHONPATH": str(eh_dir / "broken_mutation_silent_fail")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "TUT-004-S03",
                "status": "PASS",
                "check": "check_exercise_extension_hook",
                "evidence": [{"path": "examples/extension-hook", "type": "directory"}],
                "message": "Упражнение extension-hook: валидация событий хуков и блокировка опасных команд доказаны",
            })
        else:
            cases.append({
                "scenario_id": "TUT-004-S03",
                "status": "FAIL",
                "check": "check_exercise_extension_hook",
                "evidence": [{"path": "examples/extension-hook", "type": "directory"}],
                "message": f"Сбой проверки extension-hook: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 15. Проверка упражнения capstone-project (CRS-003-S03)
    cp_dir = repo_root / "examples" / "capstone-project"
    if (cp_dir / "test.py").exists() and (cp_dir / "solution").exists():
        cp_test = str((cp_dir / "test.py").resolve())
        res_sol = subprocess.run([sys.executable, cp_test], cwd=str(cp_dir / "solution"), env={"PYTHONPATH": str(cp_dir / "solution")}, capture_output=True, text=True, timeout=5)
        res_st = subprocess.run([sys.executable, cp_test], cwd=str(cp_dir / "starter"), env={"PYTHONPATH": str(cp_dir / "starter")}, capture_output=True, text=True, timeout=5)
        res_m1 = subprocess.run([sys.executable, cp_test], cwd=str(cp_dir / "broken_mutation_validation"), env={"PYTHONPATH": str(cp_dir / "broken_mutation_validation")}, capture_output=True, text=True, timeout=5)
        res_m2 = subprocess.run([sys.executable, cp_test], cwd=str(cp_dir / "broken_mutation_edge_case"), env={"PYTHONPATH": str(cp_dir / "broken_mutation_edge_case")}, capture_output=True, text=True, timeout=5)

        if res_sol.returncode == 0 and res_st.returncode != 0 and res_m1.returncode != 0 and res_m2.returncode != 0:
            cases.append({
                "scenario_id": "CRS-003-S03",
                "status": "PASS",
                "check": "check_exercise_capstone_project",
                "evidence": [{"path": "examples/capstone-project", "type": "directory"}],
                "message": "Упражнение capstone-project: комплексная обработка, валидация и граничные случаи доказаны",
            })
        else:
            cases.append({
                "scenario_id": "CRS-003-S03",
                "status": "FAIL",
                "check": "check_exercise_capstone_project",
                "evidence": [{"path": "examples/capstone-project", "type": "directory"}],
                "message": f"Сбой проверки capstone-project: sol={res_sol.returncode}, st={res_st.returncode}, m1={res_m1.returncode}, m2={res_m2.returncode}",
            })

    # 16. Проверка инструмента обновления check_updates.py (UPD-002, UPD-003)
    cu_script = repo_root / "scripts" / "check_updates.py"
    if cu_script.exists():
        r_base = subprocess.run([sys.executable, str(cu_script)], cwd=str(repo_root), capture_output=True, text=True, timeout=5)
        r_rem = subprocess.run([sys.executable, str(cu_script), "--candidate", "scripts/fixtures/updates/removed_flag.json"], cwd=str(repo_root), capture_output=True, text=True, timeout=5)
        r_unk = subprocess.run([sys.executable, str(cu_script), "--candidate", "scripts/fixtures/updates/unknown_command.json"], cwd=str(repo_root), capture_output=True, text=True, timeout=5)
        r_edt = subprocess.run([sys.executable, str(cu_script), "--candidate", "scripts/fixtures/updates/editorial_only.json"], cwd=str(repo_root), capture_output=True, text=True, timeout=5)
        r_mal = subprocess.run([sys.executable, str(cu_script), "--candidate", "scripts/fixtures/updates/malformed_response.json"], cwd=str(repo_root), capture_output=True, text=True, timeout=5)
        r_fetch = subprocess.run([sys.executable, str(cu_script), "--fetch"], cwd=str(repo_root), capture_output=True, text=True, timeout=5)

        if (
            r_base.returncode == 0
            and r_rem.returncode == 1
            and r_unk.returncode == 2
            and r_edt.returncode == 0
            and r_mal.returncode == 2
            and r_fetch.returncode == 1
        ):
            cases.append({
                "scenario_id": "UPD-002-S01",
                "status": "PASS",
                "check": "check_updates_tool",
                "evidence": [{"path": "scripts/check_updates.py", "type": "file"}],
                "message": "Скрипт check_updates.py корректно классифицирует кандидатов (COMPATIBLE/INCOMPLETE/INCOMPATIBLE) и блокирует сеть",
            })
        else:
            cases.append({
                "scenario_id": "UPD-002-S01",
                "status": "FAIL",
                "check": "check_updates_tool",
                "evidence": [{"path": "scripts/check_updates.py", "type": "file"}],
                "message": f"Сбой проверки check_updates: base={r_base.returncode}, rem={r_rem.returncode}, unk={r_unk.returncode}, edt={r_edt.returncode}, mal={r_mal.returncode}, fetch={r_fetch.returncode}",
            })

    # 17. Проверка миграции прогресса при обновлении курса (PRG-004)
    try:
        sys.path.insert(0, str(repo_root / "scripts"))
        from check_updates import migrate_progress_record

        # 1. Отклонение чужого курса
        f_res = migrate_progress_record({"course_id": "claude-tracker", "lessons": {}}, "codex-cli-course-ru", {})
        # 2. Обработка изменения revision и unlinked
        t_res = migrate_progress_record(
            {
                "schema_version": 1,
                "course_id": "codex-cli-course-ru",
                "lessons": {
                    "start.overview": {"read": True, "revision": 1},
                    "workflow.small-fix": {"read": True, "revision": 1},
                    "old.deleted": {"read": True, "revision": 1},
                },
            },
            "codex-cli-course-ru",
            {"start.overview": 1, "workflow.small-fix": 2},
        )

        if (
            not f_res["success"]
            and t_res["success"]
            and t_res["migrated_data"]["lessons"]["workflow.small-fix"]["needs_recheck"] is True
            and t_res["migrated_data"]["lessons"]["start.overview"]["needs_recheck"] is False
            and "old.deleted" in t_res["migrated_data"]["unlinked_records"]
        ):
            cases.append({
                "scenario_id": "PRG-004-S01",
                "status": "PASS",
                "check": "check_progress_migration",
                "evidence": [{"path": "scripts/check_updates.py", "type": "file"}],
                "message": "Миграция прогресса: чужой курс отклоняется, changed revision помечается recheck, удаленные уроки сохраняются",
            })
        else:
            cases.append({
                "scenario_id": "PRG-004-S01",
                "status": "FAIL",
                "check": "check_progress_migration",
                "evidence": [{"path": "scripts/check_updates.py", "type": "file"}],
                "message": f"Сбой проверки миграции прогресса: f_res={f_res}, t_res={t_res}",
            })
    except Exception as e:
        cases.append({
            "scenario_id": "PRG-004-S01",
            "status": "FAIL",
            "check": "check_progress_migration",
            "evidence": [],
            "message": f"Исключение при проверке миграции прогресса: {e}",
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


def run_live_checks(repo_root: Path, env_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    codex_ver = env_info.get("codex")
    if not codex_ver:
        cases.append({
            "scenario_id": "VAL-004-S02",
            "status": "BLOCKED",
            "check": "check_codex_availability",
            "evidence": [],
            "message": "Codex CLI не найден в окружении PATH для live-профиля",
        })
        return cases

    cases.append({
        "scenario_id": "VAL-004-S01",
        "status": "PASS",
        "check": "check_codex_availability",
        "evidence": [{"command": "codex --version", "output": codex_ver}],
        "message": f"Codex CLI обнаружен и отвечает: {codex_ver}",
    })

    # Проверка справки CLI
    try:
        r_help = subprocess.run(["codex", "--help"], capture_output=True, text=True, timeout=5)
        if r_help.returncode == 0:
            cases.append({
                "scenario_id": "VAL-004-S03",
                "status": "PASS",
                "check": "check_codex_help",
                "evidence": [{"command": "codex --help"}],
                "message": "Codex CLI выводит встроенную справку по командам",
            })
    except Exception as e:
        cases.append({
            "scenario_id": "VAL-004-S03",
            "status": "FAIL",
            "check": "check_codex_help",
            "evidence": [],
            "message": f"Ошибка вызова codex --help: {e}",
        })

    # Проверка наличия и структуры учебного наставника learn
    learn_skill = repo_root / ".agents" / "skills" / "learn" / "SKILL.md"
    if learn_skill.exists():
        content = learn_skill.read_text(encoding="utf-8")
        if "name: learn" in content and "Codex" in content:
            cases.append({
                "scenario_id": "TUT-001-S01",
                "status": "PASS",
                "check": "check_learn_tutor_skill",
                "evidence": [{"path": ".agents/skills/learn/SKILL.md", "type": "file"}],
                "message": "Учебный наставник .agents/skills/learn/SKILL.md активен и настроен для Codex",
            })
        else:
            cases.append({
                "scenario_id": "TUT-001-S01",
                "status": "FAIL",
                "check": "check_learn_tutor_skill",
                "evidence": [{"path": ".agents/skills/learn/SKILL.md", "type": "file"}],
                "message": "SKILL.md не содержит name: learn или упоминания Codex",
            })
    else:
        cases.append({
            "scenario_id": "TUT-001-S01",
            "status": "FAIL",
            "check": "check_learn_tutor_skill",
            "evidence": [],
            "message": "Файл .agents/skills/learn/SKILL.md отсутствует",
        })

    return cases


def run_release_checks(repo_root: Path, evidence_dir: Optional[Path]) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    # 1. Прогон всех офлайн-проверок
    offline_cases = run_offline_checks(repo_root)
    cases.extend(offline_cases)

    # 2. Проверка отсутствия FAIL/BLOCKED/NOT_RUN среди обязательных проверок (VAL-005)
    failing = [c for c in offline_cases if c["status"] != "PASS"]
    if failing:
        cases.append({
            "scenario_id": "VAL-005-S01",
            "status": "FAIL",
            "check": "check_release_evidence_gate",
            "evidence": [],
            "message": f"Отказ релиза: обнаружены непрошедшие проверки ({len(failing)})",
        })
    else:
        cases.append({
            "scenario_id": "VAL-005-S01",
            "status": "PASS",
            "check": "check_release_evidence_gate",
            "evidence": [{"cases_count": len(offline_cases)}],
            "message": f"Все обязательные сценарии ({len(offline_cases)}) завершились со статусом PASS",
        })

    # 3. Сборка и валидация чистоты релизного пакета (OFF-006, UPD-004)
    rel_site = repo_root / ".learning" / "release_site"
    dist_dir = repo_root / ".learning" / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dist_dir / "codex-course-release.zip"

    try:
        build_script = repo_root / "scripts" / "build_website.py"
        r_b = subprocess.run([sys.executable, str(build_script), "--output", str(rel_site)], cwd=str(repo_root), capture_output=True, text=True, timeout=30)
        if r_b.returncode != 0:
            cases.append({
                "scenario_id": "OFF-006-S01",
                "status": "FAIL",
                "check": "build_release_package",
                "evidence": [],
                "message": f"Сбой сборки релизного сайта: {r_b.stderr}",
            })
            return cases

        # Проверка манифеста и упаковка
        manifest_entries = {}
        for root, _, files in os.walk(rel_site):
            for file in files:
                fp = Path(root) / file
                rel = os.path.relpath(fp, rel_site).replace("\\", "/")
                with open(fp, "rb") as f:
                    manifest_entries[rel] = hashlib.sha256(f.read()).hexdigest()

        manifest_file = rel_site / "manifest.json"
        manifest_file.write_text(json.dumps(manifest_entries, indent=2, sort_keys=True), encoding="utf-8")

        # Создание zip
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(rel_site):
                for file in files:
                    fp = Path(root) / file
                    arcname = os.path.relpath(fp, rel_site)
                    zf.write(fp, arcname)

        # Проверка отсутствия секретов и абсолютных путей в архиве (OFF-006-S02)
        has_bad_items = False
        bad_reason = ""
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            for name in namelist:
                if ".env" in name or ".git" in name or "progress.json" in name:
                    has_bad_items = True
                    bad_reason = f"Обнаружен запрещенный файл в архиве: {name}"
                    break
                if name.startswith("assets/vendor/"):
                    continue
                if name.endswith((".html", ".js", ".json")):
                    raw = zf.read(name).decode("utf-8", errors="ignore")
                    if 'href="file:///' in raw or 'src="file:///' in raw or 'href="C:\\' in raw or 'src="C:\\' in raw:
                        has_bad_items = True
                        bad_reason = f"Обнаружена абсолютная локальная ссылка в {name}"
                        break
                    if "projects/codex-howto" in raw or "projects\\codex-howto" in raw:
                        has_bad_items = True
                        bad_reason = f"Обнаружена утечка локального пути проекта в {name}"
                        break

        if has_bad_items:
            cases.append({
                "scenario_id": "OFF-006-S02",
                "status": "FAIL",
                "check": "check_package_cleanliness",
                "evidence": [],
                "message": f"В релизном архиве обнаружены нарушения: {bad_reason}",
            })
        else:
            cases.append({
                "scenario_id": "OFF-006-S02",
                "status": "PASS",
                "check": "check_package_cleanliness",
                "evidence": [{"path": str(zip_path.relative_to(repo_root)), "type": "archive"}],
                "message": "Релизный архив не содержит секретов, .env и абсолютных путей",
            })

        cases.append({
            "scenario_id": "OFF-006-S01",
            "status": "PASS",
            "check": "build_release_package",
            "evidence": [{"archive": str(zip_path.relative_to(repo_root)), "files_count": len(manifest_entries)}],
            "message": f"Релизный архив собран: {len(manifest_entries)} файлов с манифестом SHA-256",
        })

    except Exception as e:
        cases.append({
            "scenario_id": "OFF-006-S01",
            "status": "FAIL",
            "check": "build_release_package",
            "evidence": [],
            "message": f"Исключение при сборке релиза: {e}",
        })
    finally:
        import shutil
        shutil.rmtree(rel_site, ignore_errors=True)

    return cases


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
    elif profile == "live":
        cases = run_live_checks(repo_root, env_info)
    elif profile == "release":
        cases = run_release_checks(repo_root, args.evidence_dir)

    if any(c["status"] == "FAIL" for c in cases):
        overall = "FAIL"
    elif any(c["status"] == "BLOCKED" for c in cases):
        overall = "BLOCKED"
    elif not cases:
        overall = "NOT_RUN"

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
