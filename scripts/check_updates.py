#!/usr/bin/env python3
"""scripts/check_updates.py - Автономный инструмент проверки обновлений и совместимости.

Сравнивает локальный baseline (из sources.json) с кандидатом релиза без автоматического
внесения изменений в курс, системный конфиг или окружение пользователя.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_candidate(baseline_data: Dict[str, Any], candidate_data: Dict[str, Any]) -> Dict[str, Any]:
    """Сравнивает кандидата с baseline и формирует аналитический отчет."""
    baseline_cli = baseline_data.get("target_cli", "0.160.0")
    candidate_cli = candidate_data.get("candidate_cli")

    affected_lessons: List[str] = []
    issues: List[Dict[str, Any]] = []
    status = "COMPATIBLE"
    is_editorial_only = False

    # 1. Проверка наличия версии кандидата
    if not candidate_cli:
        return {
            "status": "INCOMPLETE",
            "message": "В данных кандидата не указана версия candidate_cli",
            "affected_lessons": [],
            "issues": [{"type": "missing_version", "severity": "error"}],
            "editorial_only": False,
        }

    # 2. Проверка удаленных или измененных флагов/команд
    removed_flags = candidate_data.get("removed_flags", [])
    if removed_flags:
        status = "INCOMPATIBLE"
        for rf in removed_flags:
            flag_name = rf.get("name") if isinstance(rf, dict) else str(rf)
            lessons = rf.get("lessons", ["safety", "workflow"]) if isinstance(rf, dict) else ["safety", "workflow"]
            affected_lessons.extend(lessons)
            issues.append({
                "type": "removed_flag",
                "flag": flag_name,
                "severity": "critical",
                "lessons": lessons,
            })

    # 3. Проверка неизвестных/недокументированных возможностей
    unknown_commands = candidate_data.get("unknown_commands", [])
    if unknown_commands:
        if status != "INCOMPATIBLE":
            status = "INCOMPLETE"
        for uc in unknown_commands:
            issues.append({
                "type": "unknown_command",
                "command": uc,
                "severity": "warning",
            })

    # 4. Проверка редакционных правок документации
    doc_changes = candidate_data.get("doc_changes", [])
    if doc_changes and not removed_flags and not unknown_commands:
        is_editorial_only = True
        for dc in doc_changes:
            lessons = dc.get("lessons", ["start"])
            affected_lessons.extend(lessons)
            issues.append({
                "type": "editorial_change",
                "source_id": dc.get("source_id"),
                "severity": "info",
                "lessons": lessons,
            })

    # Удаление дубликатов в затронутых уроках
    affected_lessons = sorted(list(set(affected_lessons)))

    return {
        "status": status,
        "baseline_cli": baseline_cli,
        "candidate_cli": candidate_cli,
        "affected_lessons": affected_lessons,
        "issues": issues,
        "editorial_only": is_editorial_only,
    }


def migrate_progress_record(
    imported_progress: Dict[str, Any],
    current_course_id: str,
    current_lessons_revision: Dict[str, int],
) -> Dict[str, Any]:
    """Миграция прогресса согласно требованию PRG-004."""
    # 1. Проверка чужого course_id (например Claude)
    imported_course_id = imported_progress.get("course_id")
    if imported_course_id != current_course_id:
        return {
            "success": False,
            "error": f"Несовместимый курс: импортирован '{imported_course_id}', ожидается '{current_course_id}'",
            "migrated_data": None,
        }

    lessons = imported_progress.get("lessons", {})
    migrated_lessons: Dict[str, Any] = {}
    unlinked_records: Dict[str, Any] = {}

    for lid, ldata in lessons.items():
        if lid not in current_lessons_revision:
            # Урок удален или неизвестен в новой версии
            unlinked_records[lid] = ldata
            continue

        curr_rev = current_lessons_revision[lid]
        imported_rev = ldata.get("revision", 1)

        new_entry = dict(ldata)
        if imported_rev < curr_rev:
            # Редакция изменилась - требуется повторная проверка
            new_entry["needs_recheck"] = True
            new_entry["revision"] = curr_rev
        else:
            new_entry["needs_recheck"] = False

        migrated_lessons[lid] = new_entry

    result = {
        "schema_version": imported_progress.get("schema_version", 1),
        "course_id": current_course_id,
        "lessons": migrated_lessons,
        "unlinked_records": unlinked_records,
    }

    return {
        "success": True,
        "error": None,
        "migrated_data": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="scripts/check_updates.py - Анализ обновлений Codex CLI")
    parser.add_argument("--baseline", type=Path, default=Path("sources.json"), help="Путь к baseline (sources.json)")
    parser.add_argument("--candidate", type=Path, default=None, help="Путь к фикстуре кандидата")
    parser.add_argument("--fetch", action="store_true", help="Явно запросить сетевой сбор (по умолчанию выключен)")
    parser.add_argument("--output", type=Path, default=None, help="Путь для сохранения отчета JSON")

    args = parser.parse_args()

    if args.fetch:
        # Сеть отключена по умолчанию и в соответствии с автономностью курса
        print("ОШИБКА: Сетевой сбор недоступен в автономном режиме. Используйте локальные фикстуры (--candidate).", file=sys.stderr)
        return 1

    if not args.baseline.exists():
        print(f"ОШИБКА: Файл baseline {args.baseline} не найден.", file=sys.stderr)
        return 1

    baseline_data = load_json(args.baseline)

    if not args.candidate:
        print("Локальный baseline загружен. Кандидат не указан (--candidate). Завершение без изменений.")
        return 0

    if not args.candidate.exists():
        print(f"ОШИБКА: Кандидат {args.candidate} не существует.", file=sys.stderr)
        return 1

    try:
        candidate_data = load_json(args.candidate)
    except Exception as e:
        print(f"ОШИБКА: Поврежденный файл кандидата: {e}", file=sys.stderr)
        return 2

    report = compare_candidate(baseline_data, candidate_data)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Отчет сохранен в: {args.output}")

    print(f"Статус совместимости: {report['status']}")
    if report["affected_lessons"]:
        print(f"Затронутые уроки: {', '.join(report['affected_lessons'])}")

    if report["status"] == "INCOMPATIBLE":
        return 1
    elif report["status"] == "INCOMPLETE":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
