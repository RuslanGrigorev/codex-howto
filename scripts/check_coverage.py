#!/usr/bin/env python3
"""Проверяет связи реестра. Структурный PASS не означает полноту документации."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from course_core import check_course, contained, lessons, load_json


def check(root: Path, require_complete: bool = False) -> dict:
    root = root.resolve()
    errors = check_course(root)
    sources = load_json(root / 'sources.json')
    catalog = lessons(root)
    known_sources = {s['id'] for s in sources['sources']}
    modules = load_json(root / 'course.json')['modules']
    for m in modules:
        if not m.get('path') or not contained(root / m['path'], root).is_file():
            errors.append(f'{m["id"]}: нет страницы модуля')
        if len(m['lessons']) < 2:
            errors.append(f'{m["id"]}: модуль не содержит серии уроков')
    mapped, seen = set(), set()
    topics = sources.get('topics', [])
    for topic in topics:
        tid = topic.get('topic_id')
        if not tid or tid in seen:
            errors.append('Повтор или отсутствие topic_id')
        seen.add(tid)
        if not topic.get('source_ids') or set(topic['source_ids']) - known_sources:
            errors.append(f'{tid}: отсутствует или неизвестен источник')
        for lid in topic.get('lesson_ids', []):
            if lid not in catalog:
                errors.append(f'{tid}: неизвестный урок {lid}')
            mapped.add(lid)
        try:
            path = contained(root / topic['local_path'].split('#')[0], root)
            if not path.is_file(): errors.append(f'{tid}: нет локального объяснения')
        except (ValueError, KeyError):
            errors.append(f'{tid}: некорректный локальный путь')
        if topic.get('review_status') not in {'PENDING', 'VERIFIED'}:
            errors.append(f'{tid}: неизвестный статус редакционной проверки')
    for lid in sorted(set(catalog) - mapped):
        errors.append(f'{lid}: нет связи с темой документации')
    incomplete = (sources.get('inventory_complete') is not True or
                  bool(sources.get('open_scope_items')) or
                  any(t.get('review_status') != 'VERIFIED' for t in topics))
    if require_complete and incomplete:
        errors.append('Полнота официального перечня и редакционная проверка не подтверждены')
    return {'status': 'FAIL' if errors else 'PASS',
            'meaning': 'STRUCTURAL_MAPPING_ONLY',
            'modules': len(modules), 'lessons': len(catalog),
            'mapped_lessons': len(set(catalog) & mapped),
            'topics': len(topics), 'inventory_complete': not incomplete,
            'open_scope_items': sources.get('open_scope_items', []), 'errors': errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    try: report = check(args.root, args.require_complete)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report = {'status': 'FAIL', 'errors': [str(exc)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
