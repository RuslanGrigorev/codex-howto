"""Общие операции курса. Никаких сетевых запросов при импорте."""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

GENERATED = {'.git', '.learning', '.venv', 'venv', 'node_modules', '__pycache__',
             '.pytest_cache', '.ruff_cache', '.vendor-cache', 'site', 'site_test', 'dist'}
SAFE_ENV = {'PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'PATHEXT', 'LANG', 'LC_ALL',
            'TMP', 'TEMP', 'TMPDIR'}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()

def contained(path: Path, root: Path, *, allow_root: bool = False) -> Path:
    root, path = root.resolve(), path.resolve()
    if not path.is_relative_to(root) or (path == root and not allow_root):
        raise ValueError('Путь выходит за разрешённую область')
    return path

def source_files(root: Path):
    """Стабильный список; ошибки чтения и символические ссылки не игнорируются."""
    root = root.resolve()
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in GENERATED and not d.startswith('.codex-build-') and not d.endswith('.previous-build'))
        for name in dirs:
            if (Path(directory) / name).is_symlink():
                raise ValueError('Символическая ссылка в исходном дереве: ' + name)
        for name in sorted(files):
            if name.endswith(('.pyc', '.pyo')) or name in {'.coverage', 'coverage.xml'}:
                continue
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError('Символическая ссылка в исходном дереве: ' + name)
            yield path

def tree_hash(root: Path) -> str:
    return canonical_hash({p.relative_to(root.resolve()).as_posix(): sha256(p)
                           for p in source_files(root)})

def spec_hash(root: Path) -> str:
    spec = root / 'openspec'
    if not spec.is_dir():
        raise ValueError('Нет каталога openspec')
    return canonical_hash({p.relative_to(spec).as_posix(): sha256(p)
                           for p in sorted(spec.rglob('*')) if p.is_file()})

def clean_env(workspace: Path) -> dict[str, str]:
    """Не передаёт токены родительского процесса. Не является OS-песочницей."""
    env = {k: v for k, v in os.environ.items() if k in SAFE_ENV}
    env.update({'PYTHONPATH': str(workspace), 'PYTHONUTF8': '1',
                'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'})
    return env

def lessons(root: Path) -> dict[str, dict]:
    data = load_json(root / 'course.json')
    result = {}
    for module in data['modules']:
        for lesson in module['lessons']:
            if lesson['id'] in result:
                raise ValueError('Повтор lesson_id: ' + lesson['id'])
            result[lesson['id']] = lesson
    return result

def exercise_ids(root: Path) -> set[str]:
    return {v['exercise_id'] for v in lessons(root).values() if v.get('exercise_id')}

def check_course(root: Path) -> list[str]:
    errors = []
    try:
        catalog = lessons(root)
        if not catalog:
            raise ValueError('Пустой курс')
        for lid, lesson in catalog.items():
            if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', lid):
                errors.append(f'Некорректный ID: {lid}')
            if type(lesson.get('revision')) is not int or lesson['revision'] < 1:
                errors.append(f'{lid}: нужна положительная revision')
            for key in ('path', 'quiz_path'):
                if lesson.get(key):
                    path = contained(root / lesson[key], root)
                    if not path.is_file():
                        errors.append(f'{lid}: нет {key} {lesson[key]}')
            if lesson.get('exercise_id'):
                eid = lesson['exercise_id']
                if not re.fullmatch(r'[a-z0-9-]+', eid):
                    errors.append(f'{lid}: неправильный exercise_id')
                elif not (root / 'examples' / eid / 'test.py').is_file():
                    errors.append(f'{lid}: нет независимой проверки упражнения')
            for dep in lesson.get('dependencies', []):
                if dep not in catalog:
                    errors.append(f'{lid}: неизвестная зависимость {dep}')
            if lesson.get('quiz_path'):
                q = load_json(root / lesson['quiz_path'])
                if q.get('lesson_id') != lid or not q.get('questions'):
                    errors.append(f'{lid}: пустой или чужой квиз')
                if type(q.get('passing_score')) not in (int, float) or not 0 < q['passing_score'] <= 1:
                    errors.append(f'{lid}: неверный порог квиза')
                qids = set()
                for item in q.get('questions', []):
                    opts = item.get('options', [])
                    if not item.get('id') or item['id'] in qids:
                        errors.append(f'{lid}: повтор ID вопроса')
                    qids.add(item.get('id'))
                    if len(opts) < 2 or len({o.get('id') for o in opts}) != len(opts):
                        errors.append(f'{lid}: варианты без уникальных ID')
                    if any(type(o.get('is_correct')) is not bool for o in opts) or sum(o.get('is_correct') is True for o in opts) != 1:
                        errors.append(f'{lid}: требуется один правильный ответ')
        visiting, visited = set(), set()
        def visit(lid):
            if lid in visiting:
                raise ValueError('Цикл зависимостей уроков')
            if lid in visited or lid not in catalog:
                return
            visiting.add(lid)
            for dep in catalog[lid].get('dependencies', []): visit(dep)
            visiting.remove(lid); visited.add(lid)
        for lid in catalog: visit(lid)
        sources = load_json(root / 'sources.json')
        source_ids = {s['id'] for s in sources['sources']}
        if len(source_ids) != len(sources['sources']): errors.append('Повтор source_id')
        for source in sources['sources']:
            for lid in source.get('lesson_ids', []):
                if lid not in catalog: errors.append(f'{source["id"]}: неизвестный урок {lid}')
        for item in sources.get('coverage', []):
            if item['source_id'] not in source_ids: errors.append('Неизвестный источник покрытия')
            for lid in item.get('lesson_ids', []):
                if lid not in catalog: errors.append('Неизвестный урок покрытия: ' + lid)
            if item.get('local_path'):
                path = contained(root / item['local_path'].split('#')[0], root)
                if not path.is_file(): errors.append('Нет локального покрытия: ' + str(path))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        errors.append(str(exc))
    return errors


def learning_path(root: Path, relative: str) -> Path:
    """Validate BEFORE mkdir/write; no symlink in .learning or its descendants."""
    root = root.resolve()
    candidate = root / '.learning' / relative
    if candidate.is_symlink() or any(p.is_symlink() for p in candidate.parents):
        raise ValueError('Символические ссылки в области результатов запрещены')
    return contained(candidate, root / '.learning')
