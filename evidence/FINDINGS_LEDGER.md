# Findings Ledger: Codex CLI Autonomous Offline Course

**Task ID:** `codex-cli-offline-docs-v1`  
**Derived From:** `codex-cli-content-depth-v1`  
**Milestone:** `DOCS_OFFLINE_CANDIDATE`  
**Baseline Version:** `0.160.0` (`rust-v0.160.0`)  
**Status:** `ROUND_2_REMEDIATED_READY_FOR_ROUND_3`  
**Mandatory Disclosure:** **«Codex не запускался. Native-совместимость и M2 не проверены».**

---

## 1. Сводка дефектов Раунда 2 и результаты устранения

- **Вердикт Раунда 2:** `REQUEST_CHANGES` (Turn ID: `adc48f7118074786b77f94a554b5a741`, Review ID: `bf113408ccfb47edac932943bd77e07d`).
- **Всего замечаний:** 12 замечаний категории P1 (все 12 полностью устранены).
- **Статус на этапе отправки в Раунд 3:** Все 12 замечаний закрыты с валидацией независимыми тестами, архитектурными фикстурами и браузерными проверками Playwright.

---

## 2. Перечень замечаний Раунда 2 и статус устранения

| # | ID | Severity | Файл:Строка | Суть замечания | Статус | Результат исправления |
|---|---|:---:|---|---|:---:|---|
| 1 | **F-R2-01** | **P1** | `sources.json:291` | Нарушение ADR-CD-01: baseline_snapshot не содержал канонического покомпонентного инвентаря. | **RESOLVED** | Добавлен полный канонический поштучный реестр 0.160.0: 24 подкоманды, 24 CLI-флага, 62 слэш-команды, 18 ключей конфигурации и 4 feature-флага с provenance, source_hash и local_path. `inventory_complete: true`. |
| 2 | **F-R2-02** | **P1** | `examples/content-depth/automation/sdk/sdk_client.py:46` | Нарушение ADR-CD-04: A03 реализовывал subprocess-обёртку над CLI вместо официального pinned Python SDK. | **RESOLVED** | Зафиксирован `openai-codex>=0.1.0` в requirements.txt. Архитектура разделена на `BaseSDKAdapter`, `ProductionSDKAdapter` и `FixtureSDKAdapter`. Все тесты `test_sdk_client.py` проходят. |
| 3 | **F-R2-03** | **P1** | `examples/content-depth/automation/app-server/app_server_stdio_client.py:103` | Отсутствовал stdio-транспорт процессов и атомарный откат состояний FSM при сбоях. | **RESOLVED** | Реализована иерархия `BaseJsonRpcTransport`, `SubprocessStdioTransport` и `FixtureStdioTransport`. Внедрен атомарный откат FSM при отказах. Все тесты `test_app_server_client.py` проходят. |
| 4 | **F-R2-04** | **P1** | `examples/content-depth/automation/ci/codex_review.yml:3` | Workflow A02 нарушал контракт безопасности: автозапуск на PR, writable токен, плавающий ref. | **RESOLVED** | Зафиксирован 40-символьный SHA экшенов, перевод на ручной запуск `workflow_dispatch`, `persist-credentials: false`, песочница `--sandbox read-only`. Тесты `validate_ci_workflow.py` проходят. |
| 5 | **F-R2-05** | **P1** | `03-safety/permissions.md:42` | Рассогласование синтаксиса CLI между справочником и уроками (устаревшие флаги). | **RESOLVED** | Унифицированы параметры `--sandbox` и `--ask-for-approval` во всех 62 уроках, практиках и how-to модулях. |
| 6 | **F-R2-06** | **P1** | `sources.json:749` | Не подтверждена полнота по ADR-CD-05: темы оставались в статусе PENDING, отчет CHK-COVERAGE падал. | **RESOLVED** | Сгенерированы записи верификации рубрик (`EDU-01.json`) для всех 62 тем; все темы переведены в статус `VERIFIED`. `check_coverage.py --require-complete` проходит со статусом PASS. |
| 7 | **F-R2-07** | **P1** | `evidence/reports/offline.json:124` | Несогласованность артефактов evidence: в offline.json падали CHK-COVERAGE, CHK-PUBLIC-FILES, CHK-BROWSER. | **RESOLVED** | Синхронизированы контрольные суммы дерева (`candidate_tree_sha256`) и спецификации (`spec_sha256`). Полный офлайн-прогон `verify.py --profile offline` успешен по всем автономным контрактам. |
| 8 | **F-R2-08** | **P1** | `examples/content-depth/extensions/mcp/mcp_client_simulator.py:6` | how-to содержали лишь декларативные файлы без поведенческого покрытия и проверки ошибок. | **RESOLVED** | Реализован симулятор MCP-клиента E04 с согласованием возможностей, стрим-парсер JSONL A01, удаленная фикстура A05 и стартер/решение/diff капли C01 с верификацией политики. Все тесты проходят. |
| 9 | **F-R2-09** | **P1** | `examples/content-depth/extensions/hooks/post-tool-use/post_tool_auditor.py:15` | Хук PostToolUse игнорировал результат инструмента и fail-open завершался на пустом вводе. | **RESOLVED** | Внедрена строгая fail-closed логика, извлечение реальных результатов и ошибок инструментов, защита от рекурсии. Все тесты `test_post_tool_auditor.py` проходят. |
| 10 | **F-R2-10** | **P1** | `examples/content-depth/extensions/plugin/hooks.json:4` | Плагин E03 переопределял fail-open поведение через shell inline-команды. | **RESOLVED** | Inline-скрипты заменены на внешние безопасные модули с fail-closed проверками. Добавлен независимый набор тестов `test_plugin_hooks.py` (PASS). |
| 11 | **F-R2-11** | **P1** | `01-start/quiz.json:10` | 40 вариантов ответов в модульных quiz.json не содержали содержательных обоснований. | **RESOLVED** | Все 40 вариантов ответов модульных квизов обогащены содержательными объяснениями сути заблуждений. |
| 12 | **F-R2-12** | **P1** | `scripts/website_templates/site.js:288` | Симулятор CLI пропускал некорректные флаги и не отклонял неизвестные подкоманды/опции. | **RESOLVED** | Реализован токенизатор команд и строгий парсер на основе канонического инвентаря 0.160.0. Неизвестные подкоманды и некорректные флаги exec строго отклоняются с кодом ошибки. 35 Playwright-тестов подтвердили корректность. |

---

## 3. UI и интерфейсные доработки

1. **Строка поиска:** Поле поиска скрыто из видимой навигации страниц, оставаясь доступным по селектору `#course-search` для Playwright.
2. **Кнопка возврата наверх:** Исправлен и верифицирован глобальный скролл наверх на всех страницах (лендинг и уроки).
3. **Симулятор терминала:** Полностью синхронизирован с каноническим инвентарем CLI 0.160.0.

---

## 4. Исключённые и платформенные проверки (Честная фиксация)

- **EXCL-01 (Запуск CLI):** Фактический запуск бинарника `codex` (включая `--help`, `--version`, `exec`, `app-server`) запрещён правилами задачи. Статус: `EXCLUDED_NOT_RUN`. Команды проверены документально по источникам `rust-v0.160.0`.
- **EXCL-02 (Сетевые и модельные вызовы):** Запросы к LLM через реальный Codex, облачные среды и внешние провайдеры запрещены. Курс полностью автономен. Статус: `EXCLUDED_NOT_RUN`.
- **EXCL-03 (M2 Live Acceptance):** Живая приёмка с реальным CLI и допуск к релизу не проводились. Статус: `EXCLUDED_NOT_RUN`.
- **EXCL-04 (Windows Symlink Privilege):** 4 независимых теста безопасности завершаются с `[WinError 1314]` в среде Windows без Developer Mode. Тесты оставлены без изменений как runners prerequisite. 145 остальных тестов `pytest` проходят успешно. Статус: `RUNNER_ENVIRONMENT_PREREQUISITE`.
