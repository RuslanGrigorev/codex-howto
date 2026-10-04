<picture>
  <source media="(prefers-color-scheme: dark)" srcset="resources/logos/codex-logo-dark.svg">
  <img alt="Codex CLI: интерактивный курс и справочник" src="resources/logos/codex-logo.svg">
</picture>

<p align="center">
  <a href="https://github.com/RuslanGrigorev/codex-howto/stargazers">
    <img src="https://img.shields.io/github/stars/RuslanGrigorev/codex-howto?style=flat&color=gold" alt="GitHub Stars"/>
  </a>
  <a href="https://github.com/RuslanGrigorev/codex-howto/network/members">
    <img src="https://img.shields.io/github/forks/RuslanGrigorev/codex-howto?style=flat" alt="GitHub Forks"/>
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"/>
  </a>
  <a href="CHANGELOG.md">
    <img src="https://img.shields.io/badge/Codex_CLI-0.160.0-emerald.svg" alt="Target Codex CLI"/>
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/100%25-Offline_Ready-purple.svg" alt="100% Offline"/>
  </a>
</p>

# Codex CLI: интерактивный курс и практический справочник

Полное практическое руководство и офлайн-курс по эффективной работе с **Codex CLI**. От первого запуска и безопасного исправления багов до создания собственных навыков, локальных stdio MCP-инструментов, автоматизации в конвейерах и архитектуры расширений.

Все материалы, тесты и интерактивный сайт работают **на 100% локально** и не требуют внешнего подключения к интернету.

---

## Оглавление

- [Почему этот курс?](#почему-этот-курс)
- [Структура курса (10 модулей)](#структура-курса-10-модулей)
- [Интерактивный наставник `$learn`](#интерактивный-наставник-learn)
- [Справочник (`reference/`)](#справочник-reference)
- [Быстрый старт: запуск сайта офлайн](#быстрый-старт-запуск-сайта-офлайн)
- [Проверка и верификация (`scripts/verify.py`)](#проверка-и-верификация-scriptsverifypy)
- [English Summary](#english-summary)
- [Лицензия и благодарности](#лицензия-и-благодарности)

---

## Почему этот курс?

Официальная документация часто перечисляет флаги и синтаксис, но оставляет открытыми главные вопросы реальной разработки:
- **Как безопасно изолировать команды агента** и не дать ему удалить важные файлы (`--ask`, `--sandbox`, `--allowed-tools`)?
- **Как правильно писать `AGENTS.md`**, чтобы модель соблюдала архитектурные правила без галлюцинаций?
- **Как подключать локальные MCP-серверы** через стандартный ввод/вывод (stdio) без сложных облачных сервисов?
- **Как встроить Codex CLI в CI/CD** через неинтерактивный запуск (`codex exec`) и потоковую обработку JSONL?

Этот репозиторий содержит **готовые проверенные шаблоны, детерминированные тесты и интерактивный трекер прогресса**, доступный локально.

---

## Структура курса (10 модулей)

Учебный план разбит на 3 последовательных уровня сложности:

### Уровень 1 — Базовый
1. **[01-start](01-start/overview.md)** — **Начало работы**: установка, базовые флаги, интерактивный режим, смена провайдеров (`--provider`, `--model`).
2. **[02-workflow](02-workflow/small-fix.md)** — **Рабочий цикл**: локальное воспроизведение бага, исправление и подтверждение тестами. Включает изолированное упражнение.
3. **[03-safety](03-safety/permissions.md)** — **Безопасность и доступы**: контроль прав, песочница, прерывание сессий (`Esc` / `Ctrl+C`), политика разрешений.
4. **[04-instructions](04-instructions/agents-md.md)** — **Инструкции и правила проекта**: стандарт `AGENTS.md`, системный контекст и разграничение инструкций.

### Уровень 2 — Практический
5. **[05-sessions](05-sessions/resume.md)** — **Сессии и контекст**: возобновление диалогов (`codex resume`), управление контекстным окном, разделение истории Git и контекста сессии.
6. **[06-skills](06-skills/custom-skills.md)** — **Собственные навыки**: спецификация `SKILL.md`, YAML frontmatter, создание проектных и глобальных навыков.
7. **[07-mcp](07-mcp/local-stdio.md)** — **Локальные MCP-серверы**: протокол Model Context Protocol через локальный stdio JSON-RPC без внешних сетей.
8. **[08-automation](08-automation/non-interactive.md)** — **Автоматизация и потоки**: запуск `codex exec`, потоковый разбор JSON (`--json / --stream`), интеграция в CI/CD и скрипты.

### Уровень 3 — Продвинутый
9. **[09-extensions](09-extensions/plugins-hooks.md)** — **Расширения и hooks**: архитектура плагинов, перехватчики событий жизненного цикла сессий и изоляция сред.
10. **[10-capstone](10-capstone/final-project.md)** — **Итоговый проект**: комплексная практическая задача на исправление бага, добавление валидации и проверку детерминированными тестами.

Каждое практическое упражнение содержит:
- `starter/` — исходная заготовка для ученика.
- `solution/` — эталонное рабочее решение.
- `test.py` — детерминированный проверяющий скрипт.
- 2 ошибочные мутации, доказывающие надёжность тестов.

---

## Интерактивный наставник `$learn`

В репозиторий встроен учебный наставник для Codex CLI, реализованный в [.agents/skills/learn/SKILL.md](.agents/skills/learn/SKILL.md).

Для запуска наставника в диалоге с Codex CLI выполните:
```bash
$learn
# Или для конкретного модуля:
$learn workflow
```
Наставник:
- Проводит по материалам выбранного урока.
- Проверяет выполнение упражнений через локальный запуск тестов.
- Выдаёт подсказки строго по запросу (не спойлерит решение сразу).
- Обновляет локальный файл прогресса `.learning/progress.json`.

---

## Справочник (`reference/`)

В каталоге `reference/` собрана исчерпывающая справочная документация:
- **[commands.md](reference/commands.md)** — Полный справочник команд и CLI-флагов Codex CLI (`exec`, `resume`, `--model`, `--ask` и др.).
- **[config.md](reference/config.md)** — Спецификация конфигурации `~/.codex/config.toml` и проектных настроек.
- **[skills.md](reference/skills.md)** — Справочник разработки навыков, формат метаданных и правила композиции.

---

## Быстрый старт: запуск сайта офлайн

Сайт компилируется в автономный статический каталог со встроенными стилями, шрифтами и локальным JavaScript-трекером прогресса.

### Генерация сайта
```bash
python scripts/build_website.py --output site
```

### Просмотр
- **Без веб-сервера (протокол `file://`)**: дважды кликните по файлу `site/index.html` или выполните:
  ```powershell
  Start-Process "site\index.html"
  ```
- **Через локальный HTTP-сервер Python**:
  ```bash
  python -m http.server 8080 -d site
  ```
  И перейдите на [http://localhost:8080](http://localhost:8080).

Сайт поддерживает светлую и тёмную темы ("Terminal Luxe"), плавные скроллбары и офлайн-сохранение прогресса через `localStorage` с возможностью экспорта/импорта JSON.

---

## Проверка и верификация (`scripts/verify.py`)

Проект снабжён единым детерминированным верификатором качества:
```bash
# 1. Автономные проверки файлов, тестов упражнений и сборки сайта
python scripts/verify.py --profile offline

# 2. Проверка работы с реальным установленным Codex CLI (в изоляции)
python scripts/verify.py --profile live

# 3. Полная релизная верификация артефактов и ссылок
python scripts/verify.py --profile release
```

---

## English Summary

**Codex CLI: Interactive Course and Offline Reference Guide** is a self-contained, offline-first curriculum and practical handbook for mastering the official OpenAI Codex CLI (target version 0.160.0).

- **10 Structured Modules**: From initial setup and safety guards to `AGENTS.md`, session resumption, custom skills, local stdio MCP servers, CI streaming, and hooks.
- **7 Deterministic Exercises**: Each with starter code, reference solution, test suite, and broken mutations.
- **Interactive Mentor**: `$learn` custom skill runnable directly inside Codex CLI.
- **Zero Cloud Requirement**: Compiles to a 100% offline static website compatible with `file://`.

---

## Лицензия и благодарности

Проект распространяется под лицензией [MIT](LICENSE).

Автор адаптации и русскоязычного курса: **Руслан Григорьев** ([@RuslanGrigorev](https://github.com/RuslanGrigorev)).  
Первоначальная концепция статической сборки вдохновлена проектом `claude-howto` ([luongnv89](https://github.com/luongnv89)).
