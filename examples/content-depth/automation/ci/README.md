# A02: GitHub Actions Workflow для Codex CLI

Комплект A02 демонстрирует интеграцию Codex CLI 0.160.0 в конвейер непрерывной интеграции (CI/CD) GitHub Actions для автоматического ревью pull request и проверки стандартов проекта.

## Состав комплекта

- `README.md` — описание настройки CI, переменных окружения и прав доступа.
- `codex_review.yml` — эталонный файл рабочего процесса GitHub Actions.
- `validate_ci_workflow.py` — автономный скрипт валидации синтаксиса и безопасности workflow.

## Принципы безопасности в CI/CD

1. **Минимальные права токена**: токен GitHub Actions (`GITHUB_TOKEN`) должен иметь доступ `pull-requests: write` и `contents: read`.
2. **Неинтерактивный режим**: обязательные флаги `--approval-policy never` и `--sandbox-mode workspace-write`.
3. **Изоляция секретов**: токен API провайдера передаётся исключительно через защищённые GitHub Secrets (`CI_RUNNER_SECRET`).
