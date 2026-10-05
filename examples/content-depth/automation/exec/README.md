# A01: Автоматизация через codex exec и парсинг JSONL

Комплект A01 демонстрирует неинтерактивное пакетное выполнение задач в CI/CD и скриптах с помощью команды `codex exec` и разбора структурированного потока событий в формате JSONL.

## Состав комплекта

- `README.md` — руководство по неинтерактивной автоматизации.
- `batch_exec.py` — Python-скрипт запуска и парсинга потоковых событий.
- `sample_output.jsonl` — образец полного журнала сессии `codex exec --json`.

## Ключевые флаги автоматизации

```bash
# Неинтерактивный прогон с блокировкой всех подтверждений (fail-safe)
codex exec --approval-policy never --sandbox-mode workspace-write "Промпт"

# Потоковый машиночитаемый вывод событий
codex exec --json "Выполни линтинг" > stream.jsonl

# Ограничение максимального количества итераций агента
codex exec --max-turns 5 "Исправь форматирование"
```

## Структура потоковых событий JSONL

Каждая строка в выводе представляет отдельный валидный объект JSON:
- `{"event": "turn_start", "turn": 1}`
- `{"event": "tool_call", "tool": "run_command", "args": {"command": "pytest"}}`
- `{"event": "tool_output", "exit_code": 0, "stdout": "..."}`
- `{"event": "turn_complete", "status": "completed", "usage": {"tokens": 350}}`
