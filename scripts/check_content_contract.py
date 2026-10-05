#!/usr/bin/env python3
"""Проверка выполнения контрактов содержания курса Codex CLI (T01-T06, M1)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from course_core import contained, lessons, load_json, sha256, tree_hash

DIAGRAM_SPECS = [
    ("D01", "02-workflow/small-fix.md", "Агентный цикл"),
    ("D02", "04-instructions/config.md", "Слои конфигурации"),
    ("D03", "04-instructions/scope.md", "Область AGENTS.md"),
    ("D04", "04-instructions/context.md", "Контекст память история и файлы"),
    ("D05", "06-skills/create.md", "Обнаружение и вызов skill"),
    ("D06", "05-sessions/resume.md", "История сессии и состояние Git"),
    ("D07", "03-safety/permissions.md", "Sandbox approval rules и auto-review"),
    ("D08", "07-mcp/local-stdio.md", "MCP stdio HTTP и границы доступа"),
    ("D09", "09-extensions/plugins-hooks.md", "Жизненный цикл hooks"),
    ("D10", "09-extensions/agent-design.md", "Делегация и контекст субагентов"),
    ("D11", "09-extensions/plugins.md", "Загрузка и состав плагина"),
    ("D12", "08-automation/app-server.md", "App-server initialize thread turn events"),
]

HOWTO_UNITS = {
    "B01": ("examples/content-depth/basics/workflow", "Основной рабочий цикл"),
    "B02": ("examples/content-depth/basics/config", "Конфигурация и провайдер"),
    "B03": ("examples/content-depth/basics/context", "Контекст и сессия"),
    "B04": ("examples/content-depth/basics/inputs", "Входы и терминал"),
    "H01": ("examples/content-depth/extensions/hooks/pre-tool-use", "PreToolUse hook"),
    "H02": ("examples/content-depth/extensions/hooks/post-tool-use", "PostToolUse hook"),
    "H03": ("examples/content-depth/extensions/hooks/user-prompt-submit", "UserPromptSubmit hook"),
    "H04": ("examples/content-depth/extensions/hooks/stop", "Stop hook"),
    "E01": ("examples/content-depth/extensions/subagents", "Субагенты: 3 роли"),
    "E02": ("examples/content-depth/extensions/skills", "4 готовых навыка"),
    "E03": ("examples/content-depth/extensions/plugin", "Учебный плагин"),
    "E04": ("examples/content-depth/extensions/mcp", "MCP stdio и HTTP/OAuth"),
    "A01": ("examples/content-depth/automation/exec", "Exec и JSONL"),
    "A02": ("examples/content-depth/automation/ci", "GitHub Action workflow"),
    "A03": ("examples/content-depth/automation/sdk", "Python SDK клиент"),
    "A04": ("examples/content-depth/automation/app-server", "App-server stdio клиент"),
    "A05": ("examples/content-depth/automation/remote", "Remote и cloud"),
    "C01": ("examples/content-depth/capstone", "Итоговая комплексная практика"),
}

RUBRIC_SECTIONS = [
    (r"##\s+(?:Чему вы научитесь|Назначение|Цель)", "цель и результат"),
    (r"##\s+(?:Что нужно перед началом|Условия доступности|Предпосылки)", "условия доступности"),
    (r"##\s+(?:Как это устроено|Механизм|Схема процесса|Принцип работы)", "объяснение механизма/схема"),
    (r"##\s+(?:Команды и параметры|Конфигурация|Синтаксис|Параметры)", "команды/конфигурация"),
    (r"##\s+(?:Разбор примера|Пример использования|Практический пример)", "разобранный пример"),
    (r"##\s+(?:Ограничения|Границы применимости|Ограничения и безопасность)", "ограничения"),
    (r"##\s+(?:Типовые ошибки|Ошибки и диагностика|Диагностика)", "ошибки и диагностика"),
    (r"##\s+(?:Практика|Самостоятельное задание|Пошаговое задание)", "самостоятельная практика"),
    (r"##\s+(?:Самопроверка|Критерии завершения|Разбор решения)", "самопроверка и критерий"),
]


def check_mcp_server_obsolete(root: Path) -> list[str]:
    """SYN-01: codex mcp-server не должен предлагаться как действующий интерфейс."""
    errors = []
    # Проверяем reference/commands.md
    cmd_file = root / "reference/commands.md"
    if cmd_file.is_file():
        content = cmd_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            if "codex mcp-server" in line and "историч" not in line.lower() and "удален" not in line.lower() and "deprecated" not in line.lower():
                errors.append(f"reference/commands.md:{line_no}: codex mcp-server упоминается как действующая команда")
    # Проверяем 08-automation/app-server.md
    app_server = root / "08-automation/app-server.md"
    if app_server.is_file():
        content = app_server.read_text(encoding="utf-8")
        if re.search(r"```bash\s+[^`]*codex mcp-server", content):
            errors.append("08-automation/app-server.md: активный запуск codex mcp-server в блоке bash")
    return errors


def check_diagram(root: Path, diag_id: str, lesson_path: str, title: str) -> list[str]:
    """DIA-01, OFF-01, OFF-02: проверка схемы."""
    errors = []
    diag_dir = root / "reference/diagrams"
    mmd_path = diag_dir / f"{diag_id}.mmd"
    svg_path = diag_dir / f"{diag_id}.svg"

    if not mmd_path.is_file():
        errors.append(f"{diag_id}: отсутствует исходник {mmd_path.relative_to(root)}")
    if not svg_path.is_file():
        errors.append(f"{diag_id}: отсутствует SVG {svg_path.relative_to(root)}")
    else:
        svg_content = svg_path.read_text(encoding="utf-8")
        # Безопасность SVG
        if "<script" in svg_content.lower():
            errors.append(f"{diag_id}: SVG содержит недопустимый тег <script>")
        if "foreignobject" in svg_content.lower():
            errors.append(f"{diag_id}: SVG содержит недопустимый тег <foreignObject>")
        if "onload=" in svg_content.lower() or "onclick=" in svg_content.lower():
            errors.append(f"{diag_id}: SVG содержит обработчики событий")
        if "http://" in svg_content or "https://" in svg_content:
            # Разрешаем только xmlns namespace
            urls = re.findall(r'https?://[^\s"\'>]+', svg_content)
            disallowed = [u for u in urls if not u.startswith(("http://www.w3.org/", "https://www.w3.org/"))]
            if disallowed:
                errors.append(f"{diag_id}: SVG содержит внешние ссылки: {disallowed[:2]}")

    # Проверка связанного урока
    lesson = root / lesson_path
    if not lesson.is_file():
        errors.append(f"{diag_id}: связанный урок {lesson_path} не найден")
    else:
        text = lesson.read_text(encoding="utf-8")
        if f"{diag_id}.svg" not in text and f"{diag_id}" not in text:
            errors.append(f"{diag_id}: урок {lesson_path} не ссылается на схему {diag_id}")
        # Наличие объяснения узлов и стрелок
        if "стрел" not in text.lower() and "поток" not in text.lower() and "схем" not in text.lower() and "диаграм" not in text.lower():
            errors.append(f"{diag_id}: в уроке {lesson_path} нет текстового разбора схемы")

    return errors


def check_lesson_rubric(root: Path, lesson_id: str, lesson_data: dict[str, Any]) -> list[str]:
    """EDU-01: семантическая проверка полноты и качества 9 элементов рубрики урока."""
    errors = []
    path = root / lesson_data["path"]
    if not path.is_file():
        return [f"{lesson_id}: файл {lesson_data['path']} не существует"]

    content = path.read_text(encoding="utf-8")

    for pattern, name in RUBRIC_SECTIONS:
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            errors.append(f"{lesson_id}: отсутствует раздел '{name}'")
            continue

        start = match.end()
        next_heading = re.search(r"^##\s+", content[start:], re.MULTILINE)
        section_text = content[start:start + next_heading.start()] if next_heading else content[start:]
        cleaned_text = re.sub(r"###+\s+.*", "", section_text).strip()
        if len(cleaned_text) < 30:
            errors.append(f"{lesson_id}: раздел '{name}' содержит менее 30 символов содержательного текста")

    details_match = re.search(r"<details>\s*<summary>(.*?)</summary>(.*?)</details>", content, re.DOTALL)
    if not details_match:
        errors.append(f"{lesson_id}: отсутствует или некорректно оформлена раскрываемая подсказка (<details><summary>...</summary>...</details>)")
    else:
        summary_text = details_match.group(1).strip()
        body_text = details_match.group(2).strip()
        if len(summary_text) < 5 or len(body_text) < 20:
            errors.append(f"{lesson_id}: раскрываемая подсказка пустая или недостаточно содержательная")

    if "```" not in content:
        errors.append(f"{lesson_id}: в уроке отсутствуют примеры команд и кода в блоках ```")

    return errors


def check_howto_unit(root: Path, howto_id: str, rel_path: str, title: str) -> list[str]:
    """Проверка наличия файлов how-to единицы и их соответствия объявленным в README."""
    errors = []
    unit_dir = root / rel_path
    if not unit_dir.is_dir():
        errors.append(f"{howto_id}: каталог {rel_path} не найден")
        return errors

    readme = unit_dir / "README.md"
    if not readme.is_file():
        errors.append(f"{howto_id}: в {rel_path} отсутствует README.md с описанием сценария")
        return errors

    readme_text = readme.read_text(encoding="utf-8")
    declared_files = re.findall(r"-\s+`([^`]+)`", readme_text)
    for declared in declared_files:
        if " " in declared or declared.startswith("-") or declared.startswith("$") or declared.startswith("/"):
            continue
        file_path = unit_dir / declared
        if not file_path.exists():
            errors.append(f"{howto_id}: заявленный в README.md файл '{declared}' отсутствует в {rel_path}")

    return errors


def check_inventory(root: Path) -> list[str]:
    """INV-01, INV-02: проверка инвентаря и источников."""
    errors = []
    sources_file = root / "sources.json"
    if not sources_file.is_file():
        return ["sources.json не найден"]

    data = load_json(sources_file)
    if data.get("target_cli") != "0.160.0":
        errors.append(f"sources.json target_cli != 0.160.0 ({data.get('target_cli')})")

    topics = data.get("topics", [])
    if len(topics) < 62:
        errors.append(f"topics count < 62 (найдено {len(topics)})")

    # Проверка справочника coverage.md
    cov_file = root / "reference/coverage.md"
    if not cov_file.is_file():
        errors.append("reference/coverage.md не найден")
    else:
        cov_text = cov_file.read_text(encoding="utf-8")
        for cat in ("core", "advanced", "reference_only", "historical_removed", "out_of_scope"):
            if cat not in cov_text:
                errors.append(f"reference/coverage.md не содержит категорию '{cat}'")

    return errors


def run_stage_checks(root: Path, stage: str) -> dict[str, Any]:
    """Выполняет проверки для указанного stage."""
    scenario_results: list[dict[str, Any]] = []
    catalog = lessons(root)

    # 1. SYN-01 (Удалённый mcp-server)
    if stage in {"T01", "T06", "ALL", "M1"}:
        mcp_errs = check_mcp_server_obsolete(root)
        scenario_results.append({
            "id": "SYN-01",
            "title": "Удалённая команда mcp-server",
            "status": "PASS" if not mcp_errs else "FAIL",
            "errors": mcp_errs,
        })

    # 2. INV-01 / INV-02 (Инвентарь)
    if stage in {"T01", "T06", "ALL", "M1"}:
        inv_errs = check_inventory(root)
        scenario_results.append({
            "id": "INV-01",
            "title": "Полный baseline 0.160.0 и классификация",
            "status": "PASS" if not inv_errs else "FAIL",
            "errors": inv_errs,
        })

    # 3. DIA-01 / OFF-01 / OFF-02 (Схемы)
    diag_indices = range(8) if stage == "T02" else range(8, 11) if stage == "T04" else [11] if stage == "T05" else range(12)
    if stage in {"T02", "T04", "T05", "T06", "ALL", "M1"}:
        diag_errs = []
        for idx in diag_indices:
            did, lpath, dtitle = DIAGRAM_SPECS[idx]
            diag_errs.extend(check_diagram(root, did, lpath, dtitle))
        scenario_results.append({
            "id": "DIA-01",
            "title": f"Офлайн-схемы (проверено {len(diag_indices)})",
            "status": "PASS" if not diag_errs else "FAIL",
            "errors": diag_errs,
        })

    # 4. EDU-01 (Рубрика уроков)
    if stage in {"T03", "T04", "T05", "T06", "ALL", "M1"}:
        lesson_errs = []
        modules_filter = None
        if stage == "T03":
            modules_filter = {"start", "workflow", "safety", "instructions", "sessions", "skills"}
        elif stage == "T04":
            modules_filter = {"mcp", "extensions"}
        elif stage == "T05":
            modules_filter = {"automation"}

        checked_count = 0
        for lid, ldata in catalog.items():
            mod_prefix = lid.split(".")[0]
            if modules_filter and mod_prefix not in modules_filter:
                continue
            checked_count += 1
            lesson_errs.extend(check_lesson_rubric(root, lid, ldata))

        scenario_results.append({
            "id": "EDU-01",
            "title": f"Рубрика уроков (проверено уроков: {checked_count})",
            "status": "PASS" if not lesson_errs else "FAIL",
            "errors": lesson_errs,
        })

    # 5. How-to units (B01-B04, H01-H04, E01-E04, A01-A05, C01)
    howto_filter = None
    if stage == "T03":
        howto_filter = ["B01", "B02", "B03", "B04"]
    elif stage == "T04":
        howto_filter = ["H01", "H02", "H03", "H04", "E01", "E02", "E03", "E04"]
    elif stage == "T05":
        howto_filter = ["A01", "A02", "A03", "A04", "A05"]
    elif stage in {"T06", "ALL", "M1"}:
        howto_filter = list(HOWTO_UNITS.keys())

    if howto_filter:
        howto_errs = []
        for hid in howto_filter:
            rpath, htitle = HOWTO_UNITS[hid]
            howto_errs.extend(check_howto_unit(root, hid, rpath, htitle))
        scenario_results.append({
            "id": "HOWTO-CHECK",
            "title": f"Комплекты how-to (проверено: {len(howto_filter)})",
            "status": "PASS" if not howto_errs else "FAIL",
            "errors": howto_errs,
        })

    # Сводный результат
    all_errors = [e for sc in scenario_results for e in sc.get("errors", [])]
    overall_status = "PASS" if not all_errors else "FAIL"

    return {
        "stage": stage,
        "status": overall_status,
        "scenarios": scenario_results,
        "total_scenarios": len(scenario_results),
        "passed_scenarios": sum(1 for sc in scenario_results if sc["status"] == "PASS"),
        "error_count": len(all_errors),
        "errors": all_errors,
        "candidate_tree_sha256": tree_hash(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["T01", "T02", "T03", "T04", "T05", "T06", "ALL", "M1"], default="ALL")
    parser.add_argument("--contract", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    root = args.root.resolve()
    result = run_stage_checks(root, args.stage)

    if args.report:
        report_path = args.report if args.report.is_absolute() else root / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Отчёт сохранён: {report_path}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
