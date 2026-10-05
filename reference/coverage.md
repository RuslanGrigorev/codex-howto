# Карта покрытия официальной документации Codex CLI

Целевой документальный baseline: **Codex CLI 0.160.0** (тег репозитория `rust-v0.160.0`).
Официальные источники: [OpenAI Learn Codex CLI](https://learn.chatgpt.com/docs/codex/cli), [Репозиторий OpenAI Codex](https://github.com/openai/codex/tree/rust-v0.160.0).

Этот документ содержит классификацию всех публичных возможностей, команд, флагов, настроек конфигурации и протоколов.

---

## Категории покрытия

Каждая зарегистрированная возможность относится ровно к одной из пяти категорий:

1. **`core` (Базовый курс):**
   Ключевые возможности, составляющие повседневный цикл работы разработчика с Codex CLI: запуск, исследование проекта, планирование (`/plan`), долгоживущие цели (`/goal`), инкрементальные правки, тестирование, ревью изменений, базовые политики безопасности и песочницы, управление сессиями и контекстом. Каждая позиция `core` подробно разбирается в соответствующих уроках модулей 01–06 и обеспечена практическими заданиями.

2. **`advanced` (Продвинутый трек):**
   Расширения и механизмы автоматизации: жизненный цикл hooks, архитектура субагентов и явная делегация, создание собственных skills, упаковка плагинов, клиент-серверный протокол `app-server`, неинтерактивный `exec` с JSONL и JSON Schema, интеграция в CI/CD (GitHub Actions), официальный Python SDK, удалённое подключение (remote loopback/SSH/TLS) и облачные задачи (cloud). Представлены в модулях 07–09 с готовыми шаблонами и стендами.

3. **`reference_only` (Локальный справочник):**
   Специализированные и служебные настройки, флаги диагностики, генерация shell completion, клавиатурные сочетания, тонкие параметры терминала и второстепенные поля схемы конфигурации. Для каждой такой позиции в справочнике приведена локальная карточка: точный синтаксис, назначение, пример, ожидаемый эффект и возможные риски. Отдельный урок не выделяется во избежание размывания учебного маршрута.

4. **`historical_removed` (Исторические и удалённые интерфейсы):**
   Интерфейсы, которые присутствовали в ранних превью-версиях или документации, но были удалены либо заменены к версии 0.160.0. Главный пример — подкоманда `codex mcp-server`, которая исключена из CLI, а интеграции переведены на протокол `codex app-server`. В курсе такие элементы снабжены явным историческим предупреждением и не предлагаются в активных заданиях.

5. **`out_of_scope` (Вне области курса):**
   Возможности, не относящиеся к автономному практикуму по Codex CLI: интерфейс десктопного приложения ChatGPT Desktop / macOS app, веб-интерфейс chatgpt.com, серверные API OpenAI для прямого вызова LLM (OpenAI Python API Library), платные аккаунты организации, а также сторонние AI-ассистенты (Claude Code, GitHub Copilot, Gemini CLI). Для каждого пункта дано обоснование исключения.

---

## 1. Подкоманды CLI (`codex <subcommand>`)

| Подкоманда | Категория | Источник | Локальный материал | Описание и статус |
| --- | --- | --- | --- | --- |
| `codex login` / `logout` | `core` | docs/auth | `01-start/auth.md` | Вход, проверка статуса (`login status`), безопасный выход |
| `codex resume` | `core` | docs/sessions | `05-sessions/resume.md` | Возобновление сохранённой беседы по ID или интерактивному выбору |
| `codex fork` | `core` | docs/sessions | `05-sessions/side.md` | Создание ответвления сессии с сохранением исходной истории |
| `codex archive` / `unarchive` | `core` | docs/sessions | `05-sessions/archive.md` | Архивация и разархивация сессий |
| `codex delete` | `core` | docs/sessions | `05-sessions/archive.md` | Удаление завершённых сессий |
| `codex review` | `core` | docs/developer-commands | `02-workflow/review.md` | Автономный запуск ревью diff через CLI |
| `codex apply` | `core` | docs/developer-commands | `02-workflow/small-fix.md` | Просмотр и применение предложенных изменений кода |
| `codex exec` | `advanced` | docs/non-interactive-mode | `08-automation/non-interactive.md` | Пакетный неинтерактивный запуск с `--json`, `--output-schema` |
| `codex app-server` | `advanced` | docs/app-server | `08-automation/app-server.md` | Двунаправленный JSON-RPC сервер поверх stdio для приложений-клиентов |
| `codex mcp` | `advanced` | docs/extend/mcp | `07-mcp/official-docs.md` | Управление подключениями Model Context Protocol (`list`, `test`) |
| `codex execpolicy` | `advanced` | docs/agent-configuration/rules | `03-safety/rules.md` | Управление политиками утверждения команд и доверенными путями |
| `codex cloud` | `advanced` | docs/developer-commands | `09-extensions/remote.md` | Удалённое делегирование облачным вычислительным средам |
| `codex agents` | `advanced` | docs/agent-configuration/subagents | `09-extensions/agent-design.md` | Просмотр и проверка зарегистрированных определений субагентов |
| `codex queue` | `advanced` | docs/developer-commands | `05-sessions/side.md` | Просмотр очереди фоновых задач и сообщений |
| `codex plugin` | `advanced` | docs/extend/plugins | `09-extensions/plugins.md` | Управление плагинами, проверка манифестов, локальная установка |
| `codex remote-control` | `advanced` | docs/developer-commands | `09-extensions/remote.md` | Сессия под управлением удалённого супервизора |
| `codex completion` | `reference_only` | docs/cli-customization | `reference/commands.md` | Генерация скриптов автодополнения для bash, zsh, powershell, fish |
| `codex features` | `reference_only` | docs/developer-commands | `reference/commands.md` | Вывод списка поддерживаемых feature flags и их текущих состояний |
| `codex sandbox` | `reference_only` | docs/permissions | `reference/commands.md` | Диагностика изоляции ОС (bubblewrap, Seatbelt, Windows container) |
| `codex doctor` | `reference_only` | docs/developer-commands | `reference/commands.md` | Проверка целостности окружения, сети, Git, бинарников |
| `codex update` | `reference_only` | docs/developer-commands | `01-start/updates.md` | Механизм самообновления CLI (сверяется с тегом 0.160.0) |
| `codex debug` | `reference_only` | docs/developer-commands | `reference/commands.md` | Расширенная отладочная диагностика внутренних компонентов |
| `codex mcp-server` | `historical_removed` | upstream PR / SDK page | `08-automation/app-server.md` | Удалена из CLI 0.160.0; заменена протоколом `codex app-server` |
| `ChatGPT Desktop App UI` | `out_of_scope` | chatgpt.com/desktop | — | Графический интерфейс macOS/Windows не относится к Codex CLI |
| `OpenAI API Direct Client` | `out_of_scope` | platform.openai.com | — | Прямой вызов REST API модельных эндпоинтов — другой инструмент |

---

## 2. Параметры командной строки (Флаги запуска)

| Флаг | Категория | Назначение | Карточка / Пример |
| --- | --- | --- | --- |
| `--help` / `-h` | `core` | Справка по командам и флагам | `codex --help`, `codex exec --help` |
| `--version` / `-V` | `core` | Вывод версии CLI | `codex --version` (ожидается `0.160.0`) |
| `--cd` / `-C <DIR>` | `core` | Выбор рабочего каталога | `codex -C /path/to/project` |
| `--model` / `-m <NAME>` | `core` | Выбор имени модели | `codex -m gpt-5-codex` |
| `--sandbox <MODE>` | `core` | Режим песочницы: `read-only`, `workspace-write`, `danger-full-access` | `codex --sandbox read-only` |
| `--ask-for-approval` / `-a` | `core` | Политика утверждения действий (`on-request`, `never`) | `codex -a on-request` |
| `--config` / `-c <KEY=VAL>` | `core` | Разовое переопределение ключа конфигурации в синтаксисе TOML | `codex -c 'web_search="disabled"'` |
| `--profile` / `-p <NAME>` | `core` | Подключение профиля конфигурации (`NAME.config.toml`) | `codex -p offline-dev` |
| `--add-dir <DIR>` | `core` | Расширение рабочей области записи | `codex --add-dir ../shared-libs` |
| `--image` / `-i <PATH>` | `core` | Передача графического файла в контекст запроса | `codex -i diagram.png "Объясни архитектуру"` |
| `--search` | `core` | Включение веб-поиска для текущей сессии | `codex --search "Актуальные изменения спецификации"` |
| `--oss` / `--local-provider` | `core` | Работа с локальным LLM-провайдером (ollama, lmstudio) | `codex --oss --model llama3.3` |
| `--json` | `advanced` | Потоковый вывод событий в формате JSONL (для `exec`) | `codex exec --json "Аудит проекта"` |
| `--output-schema <FILE>` | `advanced` | Валидация финального ответа по схеме JSON Schema | `codex exec --output-schema schema.json ...` |
| `--output-last-message` / `-o` | `advanced` | Сохранение итогового текстового ответа в файл | `codex exec -o result.md "Составь отчёт"` |
| `--ephemeral` | `advanced` | Одноразовая сессия без записи в постоянную базу истории | `codex exec --ephemeral "Быстрая проверка"` |
| `--remote <TARGET>` | `advanced` | Подключение к удалённому хосту или контейнеру | `codex --remote ssh://builder.internal` |
| `--remote-auth-token-env <VAR>` | `advanced` | Переменная среды, содержащая токен для удалённого подключения | `codex --remote-auth-token-env CODEX_REMOTE_KEY` |
| `--enable` / `--disable <FLAG>` | `advanced` | Управление публичными feature flags | `codex --enable subagents --disable telemetry` |
| `--strict-config` | `reference_only` | Остановка с ошибкой при обнаружении неизвестных ключей TOML | `codex --strict-config` |
| `--no-alt-screen` | `reference_only` | Отключение полноэкранного терминального режима alternate screen | `codex --no-alt-screen` |
| `--skip-git-repo-check` | `reference_only` | Разрешение запуска в каталогах без инициализированного Git | `codex --skip-git-repo-check` |
| `--color <WHEN>` | `reference_only` | Управление ANSI-раскраской (`auto`, `always`, `never`) | `codex --color always` |
| `--dangerously-bypass-...` | `out_of_scope` | Полное отключение всех проверок безопасности (`--yolo`) | Запрещён в курсе: противоречит правилам безопасности |

---

## 3. Интерактивные Slash-команды TUI (Baseline 0.160.0)

| Команда | Категория | Назначение |
| --- | --- | --- |
| `/plan` | `core` | Переход в режим структурированного проектирования решения до внесения правок |
| `/goal` | `core` | Создание и запуск долгоживущей измеримой цели с критериями завершения |
| `/review` | `core` | Запрос независимого ревью текущего diff рабочей копии |
| `/diff` | `core` | Просмотр накопленных изменений файлов в сессии |
| `/compact` | `core` | Сжатие истории сообщений для освобождения контекстного окна |
| `/recap` | `core` | Краткая сводка принятых решений и текущего статуса |
| `/clear` | `core` | Очистка экрана терминала |
| `/exit` / `/quit` | `core` | Завершение интерактивной сессии |
| `/resume` | `core` | Выбор и возобновление другой сохранённой сессии |
| `/fork` | `core` | Ответвление текущего диалога в новую изолированную ветку |
| `/model` | `core` | Интерактивный просмотр и смена активной модели |
| `/permissions` | `core` | Инспекция текущих прав доступа и политик песочницы |
| `/skills` | `advanced` | Список доступных навыков и их явный вызов (`$skill`) |
| `/subagents` | `advanced` | Список настроенных субагентов и статус их выполнения |
| `/mcp` | `advanced` | Статус подключённых серверов MCP и доступные инструменты |
| `/hooks` | `advanced` | Список активных обработчиков событий жизненного цикла |
| `/plugins` | `advanced` | Список установленных плагинов и управление ими |
| `/agents` | `advanced` | Просмотр активных ролей и правил AGENTS.md |
| `/memories` | `advanced` | Просмотр долговременной памяти проекта (`~/.codex/memories`) |
| `/stop` | `advanced` | Принудительная остановка активной фоновой задачи или итерации цели |
| `/ps` | `advanced` | Список активных фоновых процессов и запущенных субагентов |
| `/theme` | `reference_only` | Переключение цветовой темы оформления терминала |
| `/keymap` / `/vim` | `reference_only` | Настройка горячих клавиш и режима редактирования (Emacs/Vim) |
| `/debug-config` | `reference_only` | Вывод полного распарсенного дерева активной конфигурации |
| `/statusline` | `reference_only` | Настройка элементов нижней информационной панели TUI |
| `/status` / `/usage` | `reference_only` | Счётчики использованных токенов и продолжительности сессии |
| `/voice` | `out_of_scope` | Голосовой ввод (требует системных мультимедиа-драйверов и сети) |
| `/pets` | `out_of_scope` | Пасхалка оформления TUI, не влияющая на разработку |

---

## 4. Схема конфигурации `config.toml` (Dotted Keys)

| Ключ конфигурации | Категория | Тип | Описание |
| --- | --- | --- | --- |
| `model` | `core` | `string` | Имя используемой модели по умолчанию |
| `model_reasoning_effort` | `core` | `string` | Уровень рассуждений: `low`, `medium`, `high` |
| `approval_policy` | `core` | `string` | Политика подтверждений: `on-request`, `never`, `auto` |
| `sandbox_mode` | `core` | `string` | Режим изоляции: `read-only`, `workspace-write`, `danger-full-access` |
| `web_search` | `core` | `string` | Режим поиска: `disabled`, `cached`, `live` |
| `mcp_servers.<name>.command` | `advanced` | `string` | Исполняемый файл локального MCP-сервера stdio |
| `mcp_servers.<name>.args` | `advanced` | `array[string]` | Аргументы командной строки MCP-сервера |
| `mcp_servers.<name>.env` | `advanced` | `table` | Переменные среды для процесса MCP-сервера |
| `mcp_servers.<name>.url` | `advanced` | `string` | Эндпоинт удалённого MCP-сервера (SSE/HTTP) |
| `hooks.<event>` | `advanced` | `array[table]` | Регистрация обработчиков хуков (`PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`) |
| `subagents.<name>.role` | `advanced` | `string` | Назначение роли субагента: `explorer`, `reviewer`, `implementer` |
| `subagents.<name>.permissions` | `advanced` | `table` | Ограничение прав песочницы для конкретного субагента |
| `profiles.<name>` | `advanced` | `table` | Именованные наборы параметров (`NAME.config.toml`) |
| `terminal.theme` | `reference_only` | `string` | Цветовая палитра: `dark`, `light`, `solarized-dark`, `monokai` |
| `terminal.editor` | `reference_only` | `string` | Внешний редактор для расширенного ввода (`nano`, `vim`, `code`) |
| `keybindings.mode` | `reference_only` | `string` | Режим сочетаний клавиш: `default`, `emacs`, `vim` |
| `telemetry.enabled` | `reference_only` | `boolean` | Отправка телеметрии разработчикам (рекомендуется `false`) |
| `cloud.compute_backend` | `out_of_scope` | `string` | Параметры закрытых корпоративных кластеров OpenAI |

---

## 5. Документальные источники и соответствие уроков

Все 62 урока курса строго привязаны к официальным источникам тега 0.160.0 в `sources.json`.
При чтении и автономной практике не требуется передача приватных ключей, секретов или подключение к платным сетевым шлюзам. Все учебные стенды автономны и детерминированы.
