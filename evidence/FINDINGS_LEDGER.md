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

## 4. Перечень замечаний Раунда 4 и пользовательской доработки навигации

| # | ID | Severity | Файл:Строка | Суть замечания | Статус | Результат исправления |
|---|---|:---:|---|---|:---:|---|
| 1 | **F-R4-01** | **P1** | `reference/config.md`, `coverage.md` | Синхронизация с канонической схемой config_schema (18 ключей, enum enums `untrusted`, `web_search: false`). | **RESOLVED** | Таблица 4 в `coverage.md` и примеры в `config.md` строго приведены к 18 ключам официальной схемы `config_schema.json`. Добавлен рекурсивный валидатор схемы в `check_content_contract.py`. |
| 2 | **F-R4-02** | **P1** | `sdk_client.py`, `test_sdk_client.py` | Жизненный цикл A03 SDK: отмена, отказ при неизвестной сессии, замоканный тест официального пакета. | **RESOLVED** | Добавлены `cancel_session`, типизированная ошибка `CodexSessionNotFoundError`, `test_production_adapter_mocked_surface()` в `test_sdk_client.py`. Все тесты SDK проходят (10/10). |
| 3 | **F-R4-03** | **P1** | `app_server_stdio_client.py` | A04 App-Server: атомарная очистка pending-запросов при сбое записи, рассылка типизированных ошибок при EOF. | **RESOLVED** | Реализована атомарная очистка запросов при сбое записи, широковещательное оповещение о разрыве транспорта, сохранение очереди нотификаций. Все 8 тестов проходят. |
| 4 | **F-R4-04** | **P1** | `batch_exec.py`, `test_stream_parser.py` | A01 ExecRunner: граница процессов, коды возврата, stderr, отмена и таймауты. | **RESOLVED** | Добавлены тесты ненулевых кодов возврата, сбоев stderr, отмены и таймаутов в `test_stream_parser.py`. 9/9 тестов проходят. |
| 5 | **F-R4-05** | **P1** | `codex_review.yml`, `validate_ci_workflow.py` | A02 CI: разделение на 3 изолированные стадии (`fetch_pr` -> `review` -> `publish`). | **RESOLVED** | Workflow реорганизован в 3 взаимозависимые стадии: неавторизованная материализация патча, изолированное ревью в песочнице только для чтения, публикация артефакта. Все проверки `validate_ci_workflow.py` пройдены. |
| 6 | **F-R4-06** | **P1** | `mcp_client_simulator.py`, `test_mcp_simulator.py` | E04 MCP: разделение на stdio нотификации и HTTP/OAuth с проверкой срока действия токена. | **RESOLVED** | Реализованы `StdioFixtureTransport` и `HttpOAuthFixtureTransport`, добавлен контроль срока жизни Bearer токена и тест `test_oauth_token_expiry_rejection`. Все 8 тестов проходят. |
| 7 | **F-R4-07** | **P1** | `remote_fixture.py`, `test_remote_fixture.py` | A05 Remote: разделение на loopback/SSH и облачный воркер с 4-шаговым циклом. | **RESOLVED** | Разделены адаптеры `RemoteAppServerAdapter` и `CloudWorkerAdapter`, строгий контроль подписки `CloudEntitlementError` и пошаговый цикл diff -> review -> apply -> local-tests. Все 6 тестов проходят. |
| 8 | **F-R4-08** | **P1** | `verify_capstone.py`, `test_capstone_verifier.py` | C01 Capstone: строго неизменяемый проверочный файл тестов и read-only режим. | **RESOLVED** | Независимый файл тестов защищён от любых изменений, верификатор read-only. Все 5 тестов проходят. |
| 9 | **F-R4-09** | **P1** | `site.js` | Симулятор CLI: устаревшая команда `mcp-server`. | **RESOLVED** | Команда `mcp-server` удалена из списка допустимых и перенесена в список исторически удалённых с явным сообщением об ошибке в выводе терминала. |
| 10 | **F-R4-10** | **P1** | `ENV-02.json`, `CHK-SYMLINKS.log` | Выполнение тестов символических ссылок в Linux-контейнере с фиксацией лога. | **RESOLVED** | Все 4 теста символических ссылок выполнены в Linux-контейнере `python:3.12-slim`, результат 4/4 PASS зафиксирован в `evidence/evidence/logs/CHK-SYMLINKS.log` и привязан к `ENV-02.json`. |
| 11 | **F-R4-11** | **P1** | `evidence/` | Синхронизация хеша дерева кандидатов и спецификаций во всех артефактах evidence. | **RESOLVED** | Все 24 сценария и сводные отчёты перегенерированы с единым актуальным `candidate_tree_sha256` и `spec_sha256`. |
| 12 | **F-USER-02** | **P1** | `site.css`, `landing.css`, `site.js` | Смещение при навигации по разделам справа: предыдущие строки влезали в область видимости. | **RESOLVED** | Удален дублирующий `scroll-padding-top` на `html`, оставлен строгий `scroll-margin-top: 3.85rem` на заголовках, в `site.js` реализован точный скролл с вычетом высоты липкого заголовка (`targetTop - headerH - 2`), раздел теперь позиционируется строго под верхней панелью без посторонних элементов сверху. |

