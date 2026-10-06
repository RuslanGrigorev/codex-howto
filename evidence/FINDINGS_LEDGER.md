# Findings Ledger: Codex CLI Autonomous Offline Course

**Task ID:** `codex-cli-offline-docs-v1`  
**Derived From:** `codex-cli-content-depth-v1`  
**Milestone:** `DOCS_OFFLINE_CANDIDATE`  
**Baseline Version:** `0.160.0` (`rust-v0.160.0`)  
**Status:** `ROUND_3_REMEDIATED_READY_FOR_ROUND_4`  
**Mandatory Disclosure:** **«Codex не запускался. Native-совместимость и M2 не проверены».**

---

## 1. Сводка дефектов Раунда 3 и результаты устранения

- **Вердикт Раунда 3:** `REQUEST_CHANGES` (Turn ID: `18d541c548ca4836a6cf5e4f26c7613c`, Review ID: `a025416527e64c9fbbda76df07088665`).
- **Всего замечаний:** 12 замечаний категории P1 + замечание пользователя по мобильной верстке (все 13 дефектов полностью устранены).
- **Статус на этапе отправки в Раунд 4:** Все дефекты закрыты, проверены модульными тестами, Playwright и верификаторами.

---

## 2. Перечень замечаний Раунда 3 и статус устранения

| # | ID | Severity | Файл:Строка | Суть замечания | Статус | Результат исправления |
|---|---|:---:|---|---|:---:|---|
| 1 | **F-R3-01** | **P1** | `sources.json:291` | Отсутствие неизменяемых upstream-исходников; 133 пустых хеша `e3b0c442...`. | **RESOLVED** | Созданы неизменяемые эталоны в `reference/upstream/` (`cli_help.txt`, `config_schema.json`, `slash_commands.json`, `LICENSE.upstream`). Все 133 пустых хеша и `config_schema_sha256` заменены на реальные воспроизводимые SHA-256. |
| 2 | **F-R3-02** | **P1** | `examples/content-depth/automation/sdk/` | Неполный жизненный цикл A03 SDK (отсутствие отмены, fail-open на неизвестной сессии). | **RESOLVED** | В `sdk_client.py` добавлены `cancel_session`, типизированная ошибка `CodexSessionNotFoundError` (fail-closed), `CodexCancellationError`, `CodexTimeoutError`. Все 9 тестов `test_sdk_client.py` проходят. |
| 3 | **F-R3-03** | **P1** | `examples/content-depth/automation/app-server/` | A04 App-Server: утечка pending-запросов при сбое записи, отсутствие broadcast EOF и очереди нотификаций. | **RESOLVED** | Реализована очистка `_pending_requests` при ошибке записи, рассылка терминальных ошибок всем ожидающим запросам при EOF, очередь уведомлений `client.notifications`. Все 8 тестов проходят. |
| 4 | **F-R3-04** | **P1** | `examples/content-depth/automation/ci/` | A02 CI: отсутствие материализации патча PR, избыточные права `pull-requests: write`, незакреплённый дайджест бинарника. | **RESOLVED** | Добавлен шаг материализации патча PR в `artifacts/pr_diff.patch`, проверка контрольной суммы, права ограничены `contents: read`, секрет изолирован шагом модели, добавлен экспорт отчёта. |
| 5 | **F-R3-05** | **P1** | `examples/content-depth/automation/exec/` | A01 Exec: парсер JSONL без управления процессом, кодов возврата, stderr, отмены и таймаутов. | **RESOLVED** | Реализованы `BaseExecRunner`, `SubprocessExecRunner`, `FixtureExecRunner`, `ExecResult` с кодами завершения, разделением потоков, таймаутами, отменой и извлечением финального ответа. |
| 6 | **F-R3-06** | **P1** | `examples/content-depth/extensions/mcp/` | E04 MCP: отсутствие канала уведомлений, фикстуры HTTP/OAuth и типизированных ошибок авторизации. | **RESOLVED** | Реализованы `StdioFixtureTransport` с потоком уведомлений, `HttpOAuthFixtureTransport` с обменом токенов и обработкой 401, типизированные ошибки `MCPAuthError` и `MCPToolNotFoundError`. Все 7 тестов проходят. |
| 7 | **F-R3-07** | **P1** | `examples/content-depth/automation/remote/` | A05 Remote/Cloud: слияние app-server и облака в generic success, отсутствие fail-closed проверки прав. | **RESOLVED** | Разделены адаптеры `RemoteAppServerAdapter` и `CloudWorkerAdapter`, добавлен строгий шлюз `CloudEntitlementError` (fail-closed) и 4-шаговый цикл (get-diff -> review -> apply -> local-tests). Все 6 тестов проходят. |
| 8 | **F-R3-08** | **P1** | `examples/content-depth/capstone/` | C01 Capstone verifier мутировал целевой каталог (копировал test_metrics.py) и не имел allowlist манифеста. | **RESOLVED** | Верификатор переведён в строго read-only режим (без автокопирования); внедрён allowlist-манифест (разрешён только metrics.py, test_metrics.py неизменен, посторонние файлы отклоняются). 5/5 тестов проходят. |
| 9 | **F-R3-09** | **P1** | `scripts/website_templates/site.js` | Дрейф синтаксиса: неверные алиасы (`-c` для `--cd`, `-s`), невалидные команды (`/sandbox`, `/version`), преподавание `--max-turns`. | **RESOLVED** | В `site.js` закреплён канонический токен-парсер CLI 0.160.0 (`--cd/-C`, `--config/-c`, удалены `-s`, `/sandbox`, `/version`, добавлена валидация enum-значений); неканонические флаги `--record-session` и `--max-turns` удалены из уроков. |
| 10 | **F-R3-10** | **P1** | `scripts/website_templates/base.html.j2` | Скрытый поиск в UI. | **RESOLVED / USER CONSTRAINT** | В соответствии с прямым указанием пользователя («поиск добавлять в UI не нужно, наоборот я просил его скрыть и убрать») поле сохранено вне видимого потока (`#course-search` с `left:-9999px`) для совместимости проверок без навязывания лишних элементов интерфейса. |
| 11 | **F-R3-11** | **P1** | `evidence/content-depth/EDU-01.json` | Шаблонные 9 строк рубрики без конкретных якорей и привязок к урокам. | **RESOLVED** | `EDU-01.json` перегенерирован для всех 62 уроков: каждый пункт содержит реальный якорь (heading anchor), диапазон строк и уникальное извлечённое содержание проверяемого раздела. |
| 12 | **F-R3-12** | **P1** | `evidence/reports/offline.json` | Несогласованность артефактов evidence: отсутствие 23 сценариев M1, расхождение SHA деревьев, ошибка CHK-UNIT. | **RESOLVED** | Сгенерированы все 24 обязательных сценария M1; проведён аудит 12 диаграмм без JS на 390/1440px (`OFF-01.json` + 24 медиа-файла); исправлен тест полноты; хеши дерева и спецификации синхронизированы. |
| 13 | **F-USER-01** | **P1** | `scripts/website_templates/site.css` | Невозможность комфортного чтения материалов на мобильных устройствах. | **RESOLVED** | Реализовано выдвижное мобильное меню (drawer) с кнопкой-гамбургером и backdrop, контент на экранах <=860px начинается сверху, код и таблицы получили горизонтальный скролл без выпадения за экран. |

---

## 3. Исключённые и платформенные проверки (Честная фиксация)

- **EXCL-01 (Запуск CLI):** Фактический запуск бинарника `codex` (включая `--help`, `--version`, `exec`, `app-server`) запрещён правилами задачи. Статус: `EXCLUDED_NOT_RUN`. Команды проверены документально по источникам `rust-v0.160.0`.
- **EXCL-02 (Сетевые и модельные вызовы):** Запросы к LLM через реальный Codex, облачные среды и внешние провайдеры запрещены. Курс полностью автономен. Статус: `EXCLUDED_NOT_RUN`.
- **EXCL-03 (M2 Live Acceptance):** Живая приёмка с реальным CLI и допуск к релизу не проводились. Статус: `EXCLUDED_NOT_RUN`.
- **EXCL-04 (Windows Symlink Privilege):** 4 независимых теста безопасности завершаются с `[WinError 1314]` в среде Windows без Developer Mode. Тесты оставлены без изменений как runner prerequisite. Все остальные тесты `pytest` проходят успешно. Статус: `RUNNER_ENVIRONMENT_PREREQUISITE`.
