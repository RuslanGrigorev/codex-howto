# Автоматизация в CI без выдачи лишних прав

## Чему вы научитесь

- Интегрировать Codex CLI в пайплайны непрерывной интеграции (GitHub Actions, GitLab CI).
- Разграничивать права доступа: изоляция секретов API от недоверенных Pull Request сторонних авторов.
- Использовать официальный Codex GitHub Action и CLI-раннеры с минимальными привилегиями.
- Формировать проверяемые артефакты отчетов и исключать ложные успешные статусы (False PASS).

## Что нужно перед началом

- Базовые знания о структуре конфигурационных файлов CI/CD (YAML-воркфлоу).
- Понимание моделей угроз безопасности из уроков модуля [Безопасность и песочница](../03-safety/permissions.md).
- Установленный Codex CLI 0.160.0.

## Схема процесса

Безопасная архитектура изолированного CI/CD конвейера (модель 3 задач: `fetch_pr` → `review` → `publish`):

```text
┌────────────────────────────────────────────────────────┐
│  1. fetch_pr (Без секретов, unprivileged runner)       │
│  - gh pr diff $PR > artifacts/pr_diff.patch            │
│  - Сохранение только текстового diff как артефакта     │
└───────────────────────────┬────────────────────────────┘
                            │ pr_diff.patch
                            ▼
┌────────────────────────────────────────────────────────┐
│  2. review (Доверенная база + read-only песочница)     │
│  - Чистый checkout целевой ветки (не код автора PR!)   │
│  - Проверка целостности бинарника Codex CLI (SHA-256)   │
│  - codex exec --sandbox read-only --ask-for-approval   │
│    never --json "Аудит artifacts/pr_diff.patch"        │
│  - Сохранение review_report.json в артефакты           │
└───────────────────────────┬────────────────────────────┘
                            │ review_report.json
                            ▼
┌────────────────────────────────────────────────────────┐
│  3. publish (Минимальные права pull-requests: write)   │
│  - Чтение готового JSON-отчёта                         │
│  - Публикация комментария с вердиктом в Pull Request   │
└────────────────────────────────────────────────────────┘
```

## Команды и параметры

Пример шагов запуска в CI-окружении:

```bash
# Автономная проверка проекта в CI без внешних вызовов API
python scripts/verify.py --profile offline

# Запуск Codex CLI в контейнере CI с жестким таймаутом
timeout 180 codex exec --json --sandbox read-only --ask-for-approval never "Проведи линтинг" > codex_ci_report.jsonl
```

Пример защищённого GitHub Actions workflow (`examples/content-depth/automation/ci/codex_review.yml`):

```yaml
name: Codex Trusted PR Review
on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: "Номер проверяемого Pull Request"
        required: true
        type: string

permissions:
  contents: read

jobs:
  fetch_pr:
    name: Fetch and Sanitize PR Patch Artifact
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - name: Materialize Sanitized PR Patch Artifact
        run: |
          mkdir -p artifacts
          gh pr diff "${{ inputs.pr_number }}" > artifacts/pr_diff.patch
      - uses: actions/upload-artifact@v4
        with:
          name: pr-patch-${{ inputs.pr_number }}
          path: artifacts/pr_diff.patch

  review:
    name: Trusted Read-Only Codex Review
    needs: fetch_pr
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/download-artifact@v4
        with:
          name: pr-patch-${{ inputs.pr_number }}
          path: artifacts
      - name: Run Read-Only Automated PR Review
        run: |
          codex exec \
            --sandbox read-only \
            --ask-for-approval never \
            --json \
            "Проведи аудит безопасности изменений artifacts/pr_diff.patch" \
            > artifacts/review_report.json
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pr-review-report-${{ inputs.pr_number }}
          path: artifacts/review_report.json

  publish:
    name: Publish and Summarize Review
    needs: review
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: pr-review-report-${{ inputs.pr_number }}
          path: artifacts
      - name: Post Comment to PR
        run: |
          gh pr comment "${{ inputs.pr_number }}" \
            --body "Codex Automated Review завершён. Отчёт доступен в артефактах."
```

## Разбор примера

Рассмотрим предотвращение атаки через Pull Request:

1. Злоумышленник открывает PR с кодом в `test_patch.py`, пытающимся прочитать секреты окружения и отправить их на внешний сервер.
2. В правильно настроенном CI событие `pull_request` запускается без доступа к секретам репозитория:
   - Токены доступа отсутствуют в окружении.
   - Попытка эксфильтрации проваливается.
3. Процесс ревью запускается только после проверки мейнтейнером через `workflow_dispatch`.
4. Сессия Codex запускается с `--sandbox read-only --deny-network`, блокируя любые попытки сетевых запросов из исполняемого кода.

## Ограничения и безопасность

- Никогда не используйте триггер `pull_request_target` совместно с передачей секретов в непроверенный код: это открывает прямой вектор кражи API-ключей.
- Всегда устанавливайте жесткие таймауты (`timeout 300`) для шагов с Codex CLI, чтобы избежать зависания раннеров и исчерпания CI-минут.
- Ограничивайте права токена GitHub Actions (`GITHUB_TOKEN`): выставляйте `permissions: contents: read`.

## Типовые ошибки

1. **Утечка секретов через pull_request**: передача токенов провайдера в открытый форк стороннего автора.
2. **Бесконечные зависания**: запуск `codex` в CI без флага неинтерактивного режима `exec` (процесс ждет ввода из stdin).
3. **Игнорирование ошибок в JSONL**: скрипт CI считает шаг успешным при наличии кода возврата 0, хотя внутри JSONL содержится `turn.failed`.

## Практика

1. Спроектируйте файл конфигурации CI конвейера с разделением на недоверенную фазу тестов и доверенную фазу вызова агента.
2. Настройте запуск автономных тестов проекта командой `python scripts/verify.py --profile offline`.
3. Сформулируйте правила обработки артефактов сессии: исключение дампов переменных окружения из публикуемых логов сборки.

## Самопроверка

<details>
<summary>Подсказка и критерии самопроверки</summary>

- Убедитесь, что в конфигурации воркфлоу секреты передаются только на шагах с `workflow_dispatch`.
- Проверьте, что команда запуска использует `--ask-for-approval never` и песочницу `read-only`.
- Критерий успешности: CI конвейер полностью изолирует секреты от недоверенного кода и корректно сигнализирует об ошибках.

</details>

## Проверка знаний

Ответьте на вопросы внизу страницы. В исходном репозитории они доступны в [файле вопросов](ci.quiz.json). Правильные ответы подтверждают понимание; выполнение практики фиксируется отдельно.

## Источники и доступность

Практика требует установленного Codex и доступной выбранной модели. Без модели выполните разбор примера и подготовьте ожидаемый результат; реальный запуск остаётся невыполненным. Целевая версия — 0.160.0. Документальная сверка: 2026-10-05; она не заменяет протокол запуска на вашей ОС.

[GitHub Action](https://learn.chatgpt.com/docs/github-action) · [Неинтерактивная работа](https://learn.chatgpt.com/docs/non-interactive-mode).
